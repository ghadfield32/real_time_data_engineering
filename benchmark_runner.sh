#!/usr/bin/env bash
# =============================================================================
# benchmark_runner.sh - Master Benchmark Orchestrator
# =============================================================================
# Runs end-to-end benchmarks for all 24 real-time data engineering pipelines,
# collecting timing, memory, and container metrics into JSON result files.
#
# Usage:
#   ./benchmark_runner.sh --pipeline 01                # Single pipeline
#   ./benchmark_runner.sh --pipeline 01 --runs 5       # 5 runs of pipeline 01
#   ./benchmark_runner.sh --core                       # Core pipelines P00-P06
#   ./benchmark_runner.sh --extended                   # Extended pipelines P12-P23
#   ./benchmark_runner.sh --all                        # All 24 pipelines
#   ./benchmark_runner.sh --all --runs 3               # 3 runs of every pipeline
#
# Outputs:
#   pipelines/<NN>-<name>/benchmark_results/run_<N>.json   (per-run results)
#   pipelines/comparison/results.csv                       (aggregate CSV)
#   pipelines/comparison/comparison_report.md               (markdown report)
#
# Requires: bash, docker, make, date, awk
# Works on: Linux, macOS, Git Bash / MSYS2 on Windows
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINES_DIR="${SCRIPT_DIR}/pipelines"
COMPARISON_DIR="${PIPELINES_DIR}/comparison"
LOG_DIR="${SCRIPT_DIR}/benchmark_logs"

DEFAULT_RUNS=3
MAKE_TIMEOUT=600            # seconds before we kill a hung make target
DOCKER_STATS_INTERVAL=2     # seconds between docker stats samples
STARTUP_STABILIZE_WAIT=10   # extra seconds after 'make up' before measuring

# Detect Windows (MSYS / Git Bash / Cygwin) so we can set MSYS_NO_PATHCONV
IS_WINDOWS=0
if [[ "${OSTYPE:-}" == msys* ]] || [[ "${OSTYPE:-}" == cygwin* ]] || [[ -n "${MSYSTEM:-}" ]]; then
    IS_WINDOWS=1
fi

# Color helpers (no-op if stdout is not a terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; BOLD=''; RESET=''
fi

# Pipeline registry: ID -> human-readable name
declare -A PIPELINE_NAMES=(
    [00]="Batch Baseline (dbt only)"
    [01]="Kafka + Flink + Iceberg"
    [02]="Kafka + Spark + Iceberg"
    [03]="Kafka + RisingWave"
    [04]="Redpanda + Flink + Iceberg"
    [05]="Redpanda + Spark + Iceberg"
    [06]="Redpanda + RisingWave"
    [07]="Kestra Orchestrated"
    [08]="Airflow Orchestrated"
    [09]="Dagster Orchestrated"
    [10]="Serving Comparison (ClickHouse + Metabase + Superset)"
    [11]="Observability Stack (Elementary + Soda)"
    [12]="CDC Debezium Pipeline"
    [13]="Kafka + Spark + Delta Lake"
    [14]="Kafka + Materialize"
    [15]="Kafka Streams (Java)"
    [16]="Pinot Serving"
    [17]="Druid Timeseries"
    [18]="Prefect Orchestrated"
    [19]="Mage AI"
    [20]="Kafka + Bytewax"
    [21]="Feast Feature Store"
    [22]="Hudi CDC Storage"
    [23]="Full Stack Capstone"
)

# Accumulators for the final summary table
declare -a SUMMARY_LINES=()
TOTAL_PASS=0
TOTAL_FAIL=0

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

log_info()  { printf "${CYAN}[INFO]${RESET}  %s\n" "$*"; }
log_ok()    { printf "${GREEN}[OK]${RESET}    %s\n" "$*"; }
log_warn()  { printf "${YELLOW}[WARN]${RESET}  %s\n" "$*"; }
log_err()   { printf "${RED}[ERROR]${RESET} %s\n" "$*"; }
log_bold()  { printf "${BOLD}%s${RESET}\n" "$*"; }

separator() {
    printf '%.0s=' {1..72}
    printf '\n'
}

timestamp_iso() {
    # ISO-8601 timestamp, portable across GNU and BSD date
    date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S"
}

now_epoch() {
    date +%s
}

# Run a command with a timeout. Returns the command's exit code (or 124 on timeout).
# Usage: run_with_timeout <seconds> <command> [args...]
run_with_timeout() {
    local timeout_s="$1"; shift
    if command -v timeout &>/dev/null; then
        timeout "${timeout_s}" "$@"
        return $?
    else
        # macOS / BSD fallback: run in background, wait with a deadline
        "$@" &
        local pid=$!
        local elapsed=0
        while kill -0 "$pid" 2>/dev/null; do
            sleep 1
            elapsed=$((elapsed + 1))
            if [[ $elapsed -ge $timeout_s ]]; then
                kill -9 "$pid" 2>/dev/null || true
                wait "$pid" 2>/dev/null || true
                return 124
            fi
        done
        wait "$pid" 2>/dev/null
        return $?
    fi
}

# Wrapper for docker commands that sets MSYS_NO_PATHCONV on Windows
docker_cmd() {
    if [[ $IS_WINDOWS -eq 1 ]]; then
        MSYS_NO_PATHCONV=1 docker "$@"
    else
        docker "$@"
    fi
}

# Find the pipeline directory matching a two-digit ID (e.g., "01" -> "pipelines/01-kafka-flink-iceberg")
find_pipeline_dir() {
    local id="$1"
    local match
    match=$(ls -d "${PIPELINES_DIR}/${id}-"* 2>/dev/null | head -1)
    if [[ -z "$match" || ! -d "$match" ]]; then
        return 1
    fi
    echo "$match"
}

# Extract just the directory basename (e.g., "01-kafka-flink-iceberg")
pipeline_basename() {
    basename "$1"
}

# ---------------------------------------------------------------------------
# Docker stats collection (background)
# ---------------------------------------------------------------------------
# We spawn a background subshell that polls "docker stats --no-stream" and
# writes each sample to a temp file. The caller reads the file to compute peaks.

STATS_PID=""
STATS_TMPFILE=""

start_docker_stats() {
    STATS_TMPFILE="$(mktemp "${TMPDIR:-/tmp}/bench_stats_XXXXXX")"
    (
        while true; do
            local raw
            raw="$(docker_cmd stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null || true)"
            if [[ -n "$raw" ]]; then
                echo "---SAMPLE $(now_epoch)---" >> "$STATS_TMPFILE"
                echo "$raw" >> "$STATS_TMPFILE"
            fi
            sleep "$DOCKER_STATS_INTERVAL"
        done
    ) &
    STATS_PID=$!
    disown "$STATS_PID" 2>/dev/null || true
}

stop_docker_stats() {
    if [[ -n "$STATS_PID" ]]; then
        kill "$STATS_PID" 2>/dev/null || true
        wait "$STATS_PID" 2>/dev/null || true
        STATS_PID=""
    fi
}

# Parse the stats temp file and extract peak memory (MB) and container count.
# Outputs two values on stdout: "peak_memory_mb container_count"
parse_docker_stats() {
    local tmpfile="$1"
    if [[ ! -s "$tmpfile" ]]; then
        echo "0 0"
        return
    fi

    awk '
    BEGIN { peak_total = 0; max_containers = 0 }

    /^---SAMPLE/ {
        if (sample_total > peak_total) peak_total = sample_total
        if (sample_count > max_containers) max_containers = sample_count
        sample_total = 0
        sample_count = 0
        next
    }

    /\t/ {
        # Parse memory usage (first part before " / ")
        split($0, cols, "\t")
        mem_str = cols[3]
        # Strip everything after " / " to get used memory
        sub(/ \/ .*/, "", mem_str)
        # Remove leading/trailing whitespace
        gsub(/^[ \t]+|[ \t]+$/, "", mem_str)

        mem_mb = 0
        if (index(mem_str, "GiB") > 0) {
            gsub(/GiB/, "", mem_str)
            mem_mb = mem_str * 1024
        } else if (index(mem_str, "MiB") > 0) {
            gsub(/MiB/, "", mem_str)
            mem_mb = mem_str + 0
        } else if (index(mem_str, "KiB") > 0) {
            gsub(/KiB/, "", mem_str)
            mem_mb = mem_str / 1024
        } else if (index(mem_str, "GB") > 0) {
            gsub(/GB/, "", mem_str)
            mem_mb = mem_str * 1000
        } else if (index(mem_str, "MB") > 0) {
            gsub(/MB/, "", mem_str)
            mem_mb = mem_str + 0
        }

        sample_total += mem_mb
        sample_count++
    }

    END {
        # Handle last sample
        if (sample_total > peak_total) peak_total = sample_total
        if (sample_count > max_containers) max_containers = sample_count
        printf "%.1f %d\n", peak_total, max_containers
    }
    ' "$tmpfile"
}

# ---------------------------------------------------------------------------
# Core: benchmark a single pipeline run
# ---------------------------------------------------------------------------

benchmark_one_run() {
    local pipeline_id="$1"
    local pipeline_dir="$2"
    local run_number="$3"
    local total_runs="$4"
    local pipeline_name="${PIPELINE_NAMES[$pipeline_id]:-Pipeline ${pipeline_id}}"
    local dir_name
    dir_name="$(pipeline_basename "$pipeline_dir")"
    local results_dir="${pipeline_dir}/benchmark_results"
    local run_log="${LOG_DIR}/${dir_name}_run${run_number}.log"

    local status="PASS"

    separator
    log_bold "  Pipeline ${pipeline_id}: ${pipeline_name}"
    log_bold "  Run ${run_number}/${total_runs}  |  Directory: ${dir_name}"
    separator

    mkdir -p "$results_dir"
    mkdir -p "$LOG_DIR"

    # ------------------------------------------------------------------
    # Step 1: Clean up any leftover containers from previous runs
    # ------------------------------------------------------------------
    log_info "[1/6] Cleaning up previous state..."
    (
        cd "$pipeline_dir"
        make down 2>&1 || make clean 2>&1 || true
    ) >> "$run_log" 2>&1
    # Give Docker a moment to release resources
    sleep 2

    # ------------------------------------------------------------------
    # Step 2: Record start, bring up the pipeline
    # ------------------------------------------------------------------
    local ts_start
    ts_start="$(now_epoch)"
    local ts_iso
    ts_iso="$(timestamp_iso)"

    log_info "[2/6] Starting pipeline (make up)..."
    local up_start up_end startup_time_s
    up_start="$(now_epoch)"

    local up_ok=0
    if (cd "$pipeline_dir" && run_with_timeout "$MAKE_TIMEOUT" make up >> "$run_log" 2>&1); then
        up_ok=1
    fi
    up_end="$(now_epoch)"
    startup_time_s=$((up_end - up_start))

    if [[ $up_ok -eq 0 ]]; then
        log_err "Pipeline failed to start (see ${run_log})"
        status="FAIL"
    else
        log_ok "Started in ${startup_time_s}s"
    fi

    # Allow services to stabilize
    if [[ $up_ok -eq 1 ]]; then
        log_info "Waiting ${STARTUP_STABILIZE_WAIT}s for services to stabilize..."
        sleep "$STARTUP_STABILIZE_WAIT"
    fi

    # ------------------------------------------------------------------
    # Step 3: Start background docker stats collection
    # ------------------------------------------------------------------
    log_info "[3/6] Starting resource monitoring..."
    start_docker_stats

    # ------------------------------------------------------------------
    # Step 4: Run the pipeline benchmark target
    # ------------------------------------------------------------------
    log_info "[4/6] Running benchmark (make benchmark)..."
    local bench_start bench_end bench_ok=0
    bench_start="$(now_epoch)"

    if [[ $up_ok -eq 1 ]]; then
        if (cd "$pipeline_dir" && run_with_timeout "$MAKE_TIMEOUT" make benchmark >> "$run_log" 2>&1); then
            bench_ok=1
        fi
    fi
    bench_end="$(now_epoch)"

    if [[ $bench_ok -eq 0 && "$status" == "PASS" ]]; then
        log_warn "make benchmark exited non-zero (see ${run_log})"
        status="FAIL"
    else
        log_ok "Benchmark target finished in $(( bench_end - bench_start ))s"
    fi

    # ------------------------------------------------------------------
    # Step 5: Stop stats collection, compute peak memory
    # ------------------------------------------------------------------
    log_info "[5/6] Collecting resource metrics..."
    stop_docker_stats

    local peak_memory_mb=0
    local container_count=0
    if [[ -s "$STATS_TMPFILE" ]]; then
        local stats_result
        stats_result="$(parse_docker_stats "$STATS_TMPFILE")"
        peak_memory_mb="$(echo "$stats_result" | awk '{print $1}')"
        container_count="$(echo "$stats_result" | awk '{print $2}')"
    fi
    rm -f "$STATS_TMPFILE" 2>/dev/null || true
    STATS_TMPFILE=""

    log_ok "Peak memory: ${peak_memory_mb} MB  |  Containers: ${container_count}"

    # ------------------------------------------------------------------
    # Step 6: Record end timestamp, tear down
    # ------------------------------------------------------------------
    local ts_end
    ts_end="$(now_epoch)"
    local total_elapsed_s=$((ts_end - ts_start))

    log_info "[6/6] Tearing down pipeline (make down)..."
    (cd "$pipeline_dir" && make down >> "$run_log" 2>&1) || true
    # Extra cleanup to ensure no orphans linger
    (cd "$pipeline_dir" && make clean >> "$run_log" 2>&1) || true
    sleep 2

    log_ok "Teardown complete."

    # ------------------------------------------------------------------
    # Write JSON results
    # ------------------------------------------------------------------
    local result_file="${results_dir}/run_${run_number}.json"

    cat > "$result_file" <<ENDJSON
{
  "pipeline_id": "${pipeline_id}",
  "pipeline_name": "${pipeline_name}",
  "pipeline_dir": "${dir_name}",
  "run_number": ${run_number},
  "timestamp": "${ts_iso}",
  "startup_time_s": ${startup_time_s},
  "total_elapsed_s": ${total_elapsed_s},
  "peak_memory_mb": ${peak_memory_mb},
  "container_count": ${container_count},
  "status": "${status}"
}
ENDJSON

    log_ok "Results saved to ${result_file}"

    # ------------------------------------------------------------------
    # Print run summary
    # ------------------------------------------------------------------
    echo ""
    separator
    printf "  %-22s %s\n" "Pipeline:"       "${pipeline_id} - ${pipeline_name}"
    printf "  %-22s %s\n" "Run:"             "${run_number}/${total_runs}"
    printf "  %-22s %s\n" "Status:"          "${status}"
    printf "  %-22s %ss\n" "Startup time:"   "${startup_time_s}"
    printf "  %-22s %ss\n" "Total elapsed:"  "${total_elapsed_s}"
    printf "  %-22s %s MB\n" "Peak memory:"  "${peak_memory_mb}"
    printf "  %-22s %s\n" "Containers:"      "${container_count}"
    separator
    echo ""

    # Track for final summary
    SUMMARY_LINES+=("$(printf "%-4s %-38s %-4s %6ss %8s MB %4s  %s" \
        "$pipeline_id" "$pipeline_name" "R${run_number}" \
        "$total_elapsed_s" "$peak_memory_mb" "$container_count" "$status")")

    if [[ "$status" == "PASS" ]]; then
        (( TOTAL_PASS++ )) || true
    else
        (( TOTAL_FAIL++ )) || true
    fi
}

# ---------------------------------------------------------------------------
# Orchestrate: run benchmarks for a list of pipeline IDs
# ---------------------------------------------------------------------------

run_benchmarks() {
    local -a pipeline_ids=("$@")
    local num_runs="${NUM_RUNS:-$DEFAULT_RUNS}"
    local total_pipelines=${#pipeline_ids[@]}
    local total_work=$(( total_pipelines * num_runs ))
    local completed=0

    echo ""
    separator
    log_bold "  BENCHMARK ORCHESTRATOR"
    separator
    log_info "Pipelines:  ${total_pipelines}"
    log_info "Runs each:  ${num_runs}"
    log_info "Total runs: ${total_work}"
    log_info "Log dir:    ${LOG_DIR}"
    log_info "Started at: $(timestamp_iso)"
    separator
    echo ""

    local overall_start
    overall_start="$(now_epoch)"

    for pid in "${pipeline_ids[@]}"; do
        local pdir
        if ! pdir="$(find_pipeline_dir "$pid")"; then
            log_warn "Pipeline ${pid} directory not found in ${PIPELINES_DIR} -- skipping"
            continue
        fi

        # Verify the pipeline has a Makefile
        if [[ ! -f "${pdir}/Makefile" ]]; then
            log_warn "No Makefile in ${pdir} -- skipping"
            continue
        fi

        for run_num in $(seq 1 "$num_runs"); do
            completed=$((completed + 1))
            log_info "=== Progress: ${completed}/${total_work} ==="
            benchmark_one_run "$pid" "$pdir" "$run_num" "$num_runs"
        done
    done

    local overall_end
    overall_end="$(now_epoch)"
    local overall_elapsed=$(( overall_end - overall_start ))

    # ------------------------------------------------------------------
    # Generate comparison report via the Python tooling
    # ------------------------------------------------------------------
    echo ""
    separator
    log_bold "  GENERATING COMPARISON REPORT"
    separator

    local report_script="${SCRIPT_DIR}/shared/benchmarks/report.py"
    if [[ -f "$report_script" ]]; then
        log_info "Running: python shared/benchmarks/report.py"
        (cd "$SCRIPT_DIR" && python "$report_script") || {
            log_warn "Report generation failed (non-fatal). You can run it manually:"
            log_warn "  cd ${SCRIPT_DIR} && python shared/benchmarks/report.py"
        }
    else
        log_warn "Report script not found at ${report_script}"
        log_warn "Skipping comparison report generation."
    fi

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    echo ""
    separator
    log_bold "  BENCHMARK RUN COMPLETE"
    separator
    printf "  %-22s %s\n" "Total wall time:" "${overall_elapsed}s"
    printf "  %-22s %s\n" "Pipelines tested:" "${total_pipelines}"
    printf "  %-22s %s\n" "Runs per pipeline:" "${num_runs}"
    printf "  %-22s ${GREEN}%d${RESET}\n" "Passed:" "$TOTAL_PASS"
    if [[ $TOTAL_FAIL -gt 0 ]]; then
        printf "  %-22s ${RED}%d${RESET}\n" "Failed:" "$TOTAL_FAIL"
    else
        printf "  %-22s %d\n" "Failed:" "$TOTAL_FAIL"
    fi
    echo ""
    separator
    log_bold "  RESULTS SUMMARY"
    separator
    printf "  %-4s %-38s %-4s %7s %10s %5s  %s\n" \
        "ID" "Pipeline" "Run" "Time" "Memory" "Ctrs" "Status"
    printf '  %.0s-' {1..68}
    printf '\n'
    for line in "${SUMMARY_LINES[@]}"; do
        echo "  ${line}"
    done
    separator
    echo ""
    log_info "Per-run JSON results:  pipelines/<NN>-*/benchmark_results/run_N.json"
    log_info "Full run logs:         ${LOG_DIR}/"
    if [[ -f "$report_script" ]]; then
        log_info "Comparison report:     ${COMPARISON_DIR}/comparison_report.md"
        log_info "Comparison CSV:        ${COMPARISON_DIR}/results.csv"
    fi
    echo ""
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Run end-to-end benchmarks for the real-time data engineering pipelines.

Pipeline Selection (exactly one required):
  --pipeline N       Benchmark a single pipeline by ID (00-23)
  --all              Benchmark all 24 pipelines
  --core             Benchmark core pipelines only (P00-P06)
  --extended         Benchmark extended pipelines only (P12-P23)

Options:
  --runs N           Number of runs per pipeline (default: ${DEFAULT_RUNS})
  --help, -h         Show this help message

Pipeline Directory:
  ${PIPELINES_DIR}

Examples:
  $(basename "$0") --pipeline 01                # Single pipeline, 3 runs
  $(basename "$0") --pipeline 12 --runs 5       # CDC pipeline, 5 runs
  $(basename "$0") --core                       # P00-P06, 3 runs each
  $(basename "$0") --extended                   # P12-P23, 3 runs each
  $(basename "$0") --all --runs 1               # All 24, single run each

Available Pipelines:
EOF
    for pid in $(echo "${!PIPELINE_NAMES[@]}" | tr ' ' '\n' | sort); do
        printf "  P%s  %s\n" "$pid" "${PIPELINE_NAMES[$pid]}"
    done
    echo ""
}

main() {
    local mode=""
    local single_id=""
    NUM_RUNS="$DEFAULT_RUNS"

    if [[ $# -eq 0 ]]; then
        usage
        exit 1
    fi

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --pipeline|-p)
                mode="single"
                if [[ -z "${2:-}" ]]; then
                    log_err "--pipeline requires a pipeline ID (00-23)"
                    exit 1
                fi
                # Zero-pad to two digits
                single_id="$(printf '%02d' "$2")"
                shift 2
                ;;
            --all)
                mode="all"
                shift
                ;;
            --core)
                mode="core"
                shift
                ;;
            --extended)
                mode="extended"
                shift
                ;;
            --runs|-r)
                if [[ -z "${2:-}" ]] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
                    log_err "--runs requires a positive integer"
                    exit 1
                fi
                NUM_RUNS="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                log_err "Unknown argument: $1"
                usage
                exit 1
                ;;
        esac
    done

    if [[ -z "$mode" ]]; then
        log_err "No pipeline selection specified. Use --pipeline, --all, --core, or --extended."
        usage
        exit 1
    fi

    # Validate dependencies
    for cmd in docker make awk; do
        if ! command -v "$cmd" &>/dev/null; then
            log_err "Required command '${cmd}' not found in PATH."
            exit 1
        fi
    done

    # Verify Docker daemon is reachable
    if ! docker_cmd info &>/dev/null; then
        log_err "Docker daemon is not running or not reachable."
        exit 1
    fi

    # Build the list of pipeline IDs to benchmark
    local -a pids=()
    case "$mode" in
        single)
            if [[ -z "${PIPELINE_NAMES[$single_id]+_}" ]]; then
                log_err "Unknown pipeline ID: ${single_id}. Valid range is 00-23."
                exit 1
            fi
            pids=("$single_id")
            ;;
        all)
            for i in $(seq 0 23); do
                pids+=("$(printf '%02d' "$i")")
            done
            ;;
        core)
            for i in $(seq 0 6); do
                pids+=("$(printf '%02d' "$i")")
            done
            ;;
        extended)
            for i in $(seq 12 23); do
                pids+=("$(printf '%02d' "$i")")
            done
            ;;
    esac

    export NUM_RUNS
    run_benchmarks "${pids[@]}"
}

# ---------------------------------------------------------------------------
# Cleanup trap: always stop stats collection and note interrupted runs
# ---------------------------------------------------------------------------

cleanup() {
    stop_docker_stats
    if [[ -n "${STATS_TMPFILE:-}" && -f "${STATS_TMPFILE:-}" ]]; then
        rm -f "$STATS_TMPFILE" 2>/dev/null || true
    fi
    echo ""
    log_warn "Benchmark runner interrupted. Partial results may exist."
    log_warn "Run 'make down' in any active pipeline directory to clean up."
}

trap cleanup INT TERM

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

main "$@"

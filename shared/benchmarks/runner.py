"""Cross-pipeline benchmark orchestrator.

Runs benchmarks for one or all pipelines, collects metrics,
and writes results to CSV for comparison.

Usage:
    python runner.py --pipeline 01              # Benchmark one pipeline
    python runner.py --all                      # Benchmark all pipelines
    python runner.py --all --runs 3             # 3 runs each for statistical validity
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from metrics import PipelineMetrics, DockerStatsCollector

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PIPELINES_DIR = BASE_DIR / "pipelines"
COMPARISON_DIR = PIPELINES_DIR / "comparison"

PIPELINE_NAMES = {
    "00": "Batch Baseline",
    "01": "Kafka + Flink + Iceberg",
    "02": "Kafka + Spark + Iceberg",
    "03": "Kafka + RisingWave",
    "04": "Redpanda + Flink + Iceberg",
    "05": "Redpanda + Spark + Iceberg",
    "06": "Redpanda + RisingWave",
    "07": "Kestra Orchestrated",
    "08": "Airflow Orchestrated",
    "09": "Dagster Orchestrated",
    "10": "Serving Comparison",
    "11": "Observability Stack",
}


def find_pipeline_dir(pipeline_id: str) -> Path:
    """Find the pipeline directory by numeric ID."""
    for d in sorted(PIPELINES_DIR.iterdir()):
        if d.is_dir() and d.name.startswith(f"{pipeline_id}-"):
            return d
    raise FileNotFoundError(f"Pipeline {pipeline_id} not found in {PIPELINES_DIR}")


def run_make(pipeline_dir: Path, target: str, timeout: int = 600) -> tuple[bool, float, str]:
    """Run a make target in a pipeline directory. Returns (success, elapsed, output)."""
    start = time.perf_counter()
    try:
        result = subprocess.run(
            ["make", target],
            cwd=pipeline_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.perf_counter() - start
        output = result.stdout + result.stderr
        return result.returncode == 0, elapsed, output
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        return False, elapsed, f"Timeout after {timeout}s"


def benchmark_pipeline(pipeline_id: str, run_number: int = 1) -> PipelineMetrics:
    """Run a full benchmark for a single pipeline."""
    pipeline_dir = find_pipeline_dir(pipeline_id)
    pipeline_name = PIPELINE_NAMES.get(pipeline_id, f"Pipeline {pipeline_id}")

    print(f"\n{'='*60}")
    print(f"  Benchmarking: {pipeline_id} - {pipeline_name} (Run {run_number})")
    print(f"  Directory: {pipeline_dir}")
    print(f"{'='*60}\n")

    metrics = PipelineMetrics(pipeline_id=pipeline_id, pipeline_name=pipeline_name)
    e2e_start = time.perf_counter()

    # 1. Start pipeline
    print("  [1/6] Starting pipeline...")
    ok, startup_time, output = run_make(pipeline_dir, "up", timeout=300)
    metrics.startup_time_s = round(startup_time, 2)
    if not ok:
        print(f"  [FAIL] Pipeline failed to start: {output[-500:]}")
        return metrics
    print(f"  Started in {startup_time:.1f}s")

    # Start resource monitoring
    collector = DockerStatsCollector(project_name=pipeline_dir.name)
    collector.start()

    # 2. Generate events (streaming pipelines only)
    if pipeline_id != "00":
        print("  [2/6] Generating events...")
        ok, gen_time, output = run_make(pipeline_dir, "generate", timeout=600)
        metrics.ingestion_time_s = round(gen_time, 2)
        if not ok:
            print(f"  [WARN] Generation issue: {output[-300:]}")
        else:
            print(f"  Generated in {gen_time:.1f}s")
            # Try to parse generator metrics
            gen_metrics_path = pipeline_dir / "benchmark_results" / "generator_metrics.json"
            if gen_metrics_path.exists():
                with open(gen_metrics_path) as f:
                    gm = json.load(f)
                    metrics.events_produced = gm.get("events", 0)
                    metrics.events_per_second = gm.get("events_per_second", 0)
    else:
        print("  [2/6] Skipping (batch pipeline)")

    # 3. Wait for processing
    if pipeline_id != "00":
        print("  [3/6] Waiting for stream processing...")
        ok, proc_time, output = run_make(pipeline_dir, "process", timeout=600)
        metrics.processing_time_s = round(proc_time, 2)
        print(f"  Processing complete in {proc_time:.1f}s")
    else:
        print("  [3/6] Skipping (batch pipeline)")

    # 4. Run dbt build
    print("  [4/6] Running dbt build...")
    ok, dbt_time, output = run_make(pipeline_dir, "dbt-build", timeout=300)
    metrics.dbt_build_time_s = round(dbt_time, 2)
    metrics.dbt_test_pass = ok
    print(f"  dbt build: {dbt_time:.1f}s ({'PASS' if ok else 'FAIL'})")

    # 5. Stop resource monitoring
    print("  [5/6] Collecting resource metrics...")
    resource_stats = collector.stop()
    metrics.peak_memory_mb = round(resource_stats.get("peak_memory_mb", 0), 1)
    metrics.peak_cpu_percent = round(resource_stats.get("peak_cpu_percent", 0), 1)
    metrics.avg_memory_mb = round(resource_stats.get("avg_memory_mb", 0), 1)
    metrics.container_count = resource_stats.get("container_count", 0)
    metrics.container_stats = resource_stats.get("container_stats", {})

    # 6. Total E2E time
    metrics.total_e2e_time_s = round(time.perf_counter() - e2e_start, 2)

    # Stop pipeline
    print("  [6/6] Stopping pipeline...")
    run_make(pipeline_dir, "down", timeout=120)

    # Summary
    print(f"\n  --- Results ---")
    print(f"  E2E Total:    {metrics.total_e2e_time_s:.1f}s")
    print(f"  Startup:      {metrics.startup_time_s:.1f}s")
    print(f"  Ingestion:    {metrics.ingestion_time_s:.1f}s")
    print(f"  Processing:   {metrics.processing_time_s:.1f}s")
    print(f"  dbt Build:    {metrics.dbt_build_time_s:.1f}s")
    print(f"  Peak Memory:  {metrics.peak_memory_mb:.0f} MB")
    print(f"  Peak CPU:     {metrics.peak_cpu_percent:.0f}%")
    print(f"  Containers:   {metrics.container_count}")
    if metrics.events_produced:
        print(f"  Events:       {metrics.events_produced:,} ({metrics.events_per_second:,.0f}/s)")

    # Write results
    results_dir = pipeline_dir / "benchmark_results"
    results_dir.mkdir(exist_ok=True)
    results_file = results_dir / f"run_{run_number}.json"
    with open(results_file, "w") as f:
        json.dump({
            "pipeline_id": metrics.pipeline_id,
            "pipeline_name": metrics.pipeline_name,
            "run": run_number,
            "startup_time_s": metrics.startup_time_s,
            "ingestion_time_s": metrics.ingestion_time_s,
            "processing_time_s": metrics.processing_time_s,
            "dbt_build_time_s": metrics.dbt_build_time_s,
            "total_e2e_time_s": metrics.total_e2e_time_s,
            "events_produced": metrics.events_produced,
            "events_per_second": metrics.events_per_second,
            "peak_memory_mb": metrics.peak_memory_mb,
            "peak_cpu_percent": metrics.peak_cpu_percent,
            "avg_memory_mb": metrics.avg_memory_mb,
            "container_count": metrics.container_count,
            "dbt_test_pass": metrics.dbt_test_pass,
        }, f, indent=2)

    return metrics


def write_comparison_csv(all_metrics: list[PipelineMetrics]):
    """Write combined results to comparison CSV."""
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = COMPARISON_DIR / "results.csv"

    headers = [
        "pipeline_id", "pipeline_name",
        "startup_s", "ingestion_s", "processing_s", "dbt_build_s", "e2e_total_s",
        "events", "events_per_sec",
        "peak_memory_mb", "peak_cpu_pct", "avg_memory_mb", "containers",
        "dbt_pass",
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for m in all_metrics:
            writer.writerow([
                m.pipeline_id, m.pipeline_name,
                m.startup_time_s, m.ingestion_time_s, m.processing_time_s,
                m.dbt_build_time_s, m.total_e2e_time_s,
                m.events_produced, m.events_per_second,
                m.peak_memory_mb, m.peak_cpu_percent, m.avg_memory_mb,
                m.container_count, m.dbt_test_pass,
            ])

    print(f"\n  Comparison CSV written to: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="Pipeline benchmark runner")
    parser.add_argument("--pipeline", "-p", help="Pipeline ID to benchmark (e.g., 01)")
    parser.add_argument("--all", action="store_true", help="Benchmark all pipelines")
    parser.add_argument("--core", action="store_true", help="Benchmark Tier 1 only (00-06)")
    parser.add_argument("--runs", type=int, default=1, help="Runs per pipeline (default: 1)")
    args = parser.parse_args()

    if args.all:
        pipeline_ids = sorted(PIPELINE_NAMES.keys())
    elif args.core:
        pipeline_ids = [f"{i:02d}" for i in range(7)]
    elif args.pipeline:
        pipeline_ids = [args.pipeline.zfill(2)]
    else:
        parser.print_help()
        sys.exit(1)

    all_metrics = []
    for pid in pipeline_ids:
        for run in range(1, args.runs + 1):
            try:
                metrics = benchmark_pipeline(pid, run)
                all_metrics.append(metrics)
            except FileNotFoundError as e:
                print(f"  [SKIP] {e}")
            except Exception as e:
                print(f"  [ERROR] Pipeline {pid}: {e}")

    if all_metrics:
        write_comparison_csv(all_metrics)
        print(f"\n  Benchmarked {len(all_metrics)} pipeline run(s)")


if __name__ == "__main__":
    main()

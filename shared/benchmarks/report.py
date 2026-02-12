"""Generate comparison report from benchmark results.

Reads pipelines/comparison/results.csv and generates:
  - pipelines/comparison/comparison_report.md (Markdown)

Usage:
    python report.py
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
COMPARISON_DIR = BASE_DIR / "pipelines" / "comparison"
CSV_PATH = COMPARISON_DIR / "results.csv"
REPORT_PATH = COMPARISON_DIR / "comparison_report.md"


def read_results() -> list[dict]:
    if not CSV_PATH.exists():
        print(f"No results found at {CSV_PATH}")
        print("Run benchmarks first: python runner.py --all")
        return []
    with open(CSV_PATH, newline="") as f:
        return list(csv.DictReader(f))


def generate_report(results: list[dict]) -> str:
    lines = []
    lines.append("# Pipeline Comparison Report")
    lines.append("")
    lines.append("Auto-generated from benchmark results.")
    lines.append("")

    # --- Tier 1: Core Pipelines ---
    tier1 = [r for r in results if r["pipeline_id"] in [f"{i:02d}" for i in range(7)]]
    if tier1:
        lines.append("## Tier 1: Core Pipeline Comparison")
        lines.append("")
        lines.append("| Pipeline | Ingestion (evt/s) | Processing (s) | dbt Build (s) | E2E Total (s) | Peak Mem (MB) | Peak CPU (%) | Containers | dbt Pass |")
        lines.append("|----------|-------------------|----------------|---------------|---------------|---------------|--------------|------------|----------|")
        for r in tier1:
            evt_s = r["events_per_sec"] if float(r.get("events_per_sec", 0)) > 0 else "-"
            proc = r["processing_s"] if float(r.get("processing_s", 0)) > 0 else "-"
            lines.append(
                f"| {r['pipeline_id']} {r['pipeline_name'][:30]} "
                f"| {evt_s} | {proc} | {r['dbt_build_s']} | {r['e2e_total_s']} "
                f"| {r['peak_memory_mb']} | {r['peak_cpu_pct']} | {r['containers']} "
                f"| {'PASS' if r['dbt_pass'] == 'True' else 'FAIL'} |"
            )
        lines.append("")

        # Isolated comparisons
        lines.append("### Kafka vs Redpanda (Broker Comparison)")
        lines.append("")
        lines.append("Holding processing + storage constant, only the broker differs:")
        lines.append("")
        pairs = [("01", "04", "Flink+Iceberg"), ("02", "05", "Spark+Iceberg"), ("03", "06", "RisingWave")]
        for kafka_id, redpanda_id, processor in pairs:
            k = next((r for r in tier1 if r["pipeline_id"] == kafka_id), None)
            rp = next((r for r in tier1 if r["pipeline_id"] == redpanda_id), None)
            if k and rp:
                lines.append(f"- **{processor}**: Kafka {k['e2e_total_s']}s vs Redpanda {rp['e2e_total_s']}s")
        lines.append("")

        lines.append("### Flink vs Spark vs RisingWave (Processor Comparison)")
        lines.append("")
        lines.append("Holding Kafka as broker, only the processor differs:")
        lines.append("")
        for pid, name in [("01", "Flink"), ("02", "Spark"), ("03", "RisingWave")]:
            r = next((r for r in tier1 if r["pipeline_id"] == pid), None)
            if r:
                lines.append(f"- **{name}**: E2E {r['e2e_total_s']}s, Peak Memory {r['peak_memory_mb']}MB")
        lines.append("")

    # --- Tier 2: Orchestration ---
    tier2 = [r for r in results if r["pipeline_id"] in ["07", "08", "09"]]
    if tier2:
        lines.append("## Tier 2: Orchestration Comparison")
        lines.append("")
        lines.append("| Orchestrator | E2E Total (s) | dbt Build (s) | Peak Mem (MB) | Containers | dbt Pass |")
        lines.append("|-------------|---------------|---------------|---------------|------------|----------|")
        for r in tier2:
            lines.append(
                f"| {r['pipeline_name']} | {r['e2e_total_s']} | {r['dbt_build_s']} "
                f"| {r['peak_memory_mb']} | {r['containers']} "
                f"| {'PASS' if r['dbt_pass'] == 'True' else 'FAIL'} |"
            )
        lines.append("")

    # --- Tier 3: Serving ---
    tier3 = [r for r in results if r["pipeline_id"] == "10"]
    if tier3:
        lines.append("## Tier 3: Serving Layer")
        lines.append("")
        lines.append("See `pipelines/10-serving-comparison/benchmark_results/` for detailed query latencies.")
        lines.append("")

    # --- Tier 4: Observability ---
    tier4 = [r for r in results if r["pipeline_id"] == "11"]
    if tier4:
        lines.append("## Tier 4: Observability")
        lines.append("")
        lines.append("See `pipelines/11-observability-stack/observability_results/` for quality reports.")
        lines.append("")

    # --- Recommendations ---
    if tier1:
        lines.append("## Recommendations")
        lines.append("")
        fastest = min(tier1, key=lambda r: float(r["e2e_total_s"]))
        simplest = min(tier1, key=lambda r: int(r["containers"]))
        lightest = min(tier1, key=lambda r: float(r["peak_memory_mb"]))
        lines.append(f"- **Fastest E2E**: {fastest['pipeline_id']} {fastest['pipeline_name']} ({fastest['e2e_total_s']}s)")
        lines.append(f"- **Simplest (fewest containers)**: {simplest['pipeline_id']} {simplest['pipeline_name']} ({simplest['containers']} containers)")
        lines.append(f"- **Lightest (least memory)**: {lightest['pipeline_id']} {lightest['pipeline_name']} ({lightest['peak_memory_mb']}MB)")
        lines.append("")

    return "\n".join(lines)


def main():
    results = read_results()
    if not results:
        return

    report = generate_report(results)

    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Report written to: {REPORT_PATH}")
    print(f"Results from {len(results)} pipeline runs")


if __name__ == "__main__":
    main()

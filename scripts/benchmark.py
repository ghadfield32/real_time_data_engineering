"""Performance benchmarking for the dbt project.

Compares build times across different strategies:
1. Full refresh build (rebuild everything from scratch)
2. Incremental build (only new data)
3. Selective builds (individual layers)
4. Model-specific timings

Usage:
    uv run python scripts/benchmark.py
    uv run python scripts/benchmark.py --runs 3
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
DBT_DIR = BASE_DIR / "nyc_taxi_dbt"
DB_PATH = BASE_DIR / "dev.duckdb"


def run_dbt(*args: str, label: str = "") -> tuple[float, bool]:
    """Run a dbt command and return (elapsed_seconds, success)."""
    cmd = ["uv", "run", "dbt", *args, "--profiles-dir", "."]
    start = time.perf_counter()
    result = subprocess.run(cmd, cwd=DBT_DIR, capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    success = result.returncode == 0
    if not success and label:
        print(f"    [WARN] {label} failed: {result.stderr[-200:]}")
    return elapsed, success


def run_benchmark(runs: int = 1) -> dict:
    """Run all benchmarks and return timing results."""
    results = {}

    print("\n--- Benchmark: Full Refresh Build ---")
    times = []
    for i in range(runs):
        elapsed, ok = run_dbt("build", "--full-refresh", label=f"full-refresh run {i+1}")
        if ok:
            times.append(elapsed)
            print(f"  Run {i+1}/{runs}: {elapsed:.2f}s")
    if times:
        results["full_refresh"] = {"times": times, "avg": sum(times) / len(times)}
        print(f"  Average: {results['full_refresh']['avg']:.2f}s")

    print("\n--- Benchmark: Incremental Build (no new data) ---")
    times = []
    for i in range(runs):
        elapsed, ok = run_dbt("build", label=f"incremental run {i+1}")
        if ok:
            times.append(elapsed)
            print(f"  Run {i+1}/{runs}: {elapsed:.2f}s")
    if times:
        results["incremental"] = {"times": times, "avg": sum(times) / len(times)}
        print(f"  Average: {results['incremental']['avg']:.2f}s")

    print("\n--- Benchmark: Layer-by-Layer ---")
    layers = [
        ("seed", ["seed"]),
        ("staging", ["run", "--select", "staging"]),
        ("intermediate", ["run", "--select", "intermediate"]),
        ("marts_core", ["run", "--select", "marts.core"]),
        ("marts_analytics", ["run", "--select", "marts.analytics"]),
        ("tests", ["test"]),
    ]
    for layer_name, dbt_args in layers:
        elapsed, ok = run_dbt(*dbt_args, label=layer_name)
        if ok:
            results[f"layer_{layer_name}"] = {"times": [elapsed], "avg": elapsed}
            print(f"  {layer_name}: {elapsed:.2f}s")

    print("\n--- Benchmark: Individual Model Runs ---")
    models = [
        "stg_yellow_trips",
        "int_trip_metrics",
        "int_daily_summary",
        "fct_trips",
        "mart_daily_revenue",
        "mart_location_performance",
    ]
    for model_name in models:
        elapsed, ok = run_dbt("run", "--select", model_name, label=model_name)
        if ok:
            results[f"model_{model_name}"] = {"times": [elapsed], "avg": elapsed}
            print(f"  {model_name}: {elapsed:.2f}s")

    print("\n--- Benchmark: fct_trips Full Refresh vs Incremental ---")
    elapsed_fr, ok = run_dbt("run", "--select", "fct_trips", "--full-refresh", label="fct_trips full-refresh")
    if ok:
        results["fct_trips_full_refresh"] = {"times": [elapsed_fr], "avg": elapsed_fr}
        print(f"  Full refresh: {elapsed_fr:.2f}s")

    elapsed_inc, ok = run_dbt("run", "--select", "fct_trips", label="fct_trips incremental")
    if ok:
        results["fct_trips_incremental"] = {"times": [elapsed_inc], "avg": elapsed_inc}
        print(f"  Incremental:  {elapsed_inc:.2f}s")

    if "fct_trips_full_refresh" in results and "fct_trips_incremental" in results:
        speedup = results["fct_trips_full_refresh"]["avg"] / max(results["fct_trips_incremental"]["avg"], 0.01)
        print(f"  Speedup: {speedup:.1f}x")

    return results


def print_summary(results: dict):
    """Print a formatted summary table."""
    print("\n" + "=" * 55)
    print("  BENCHMARK SUMMARY")
    print("=" * 55)
    print(f"  {'Benchmark':<35} {'Avg (s)':>8} {'Runs':>6}")
    print(f"  {'-'*35} {'-'*8} {'-'*6}")

    for name, data in sorted(results.items()):
        avg = data["avg"]
        runs = len(data["times"])
        print(f"  {name:<35} {avg:>7.2f}s {runs:>5}")

    # Row counts
    print(f"\n  {'--- Row Counts ---':^50}")
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        for table, schema in [
            ("stg_yellow_trips", "staging"),
            ("int_trip_metrics", "intermediate"),
            ("fct_trips", "marts"),
            ("mart_daily_revenue", "marts"),
        ]:
            count = con.execute(f"SELECT count(*) FROM {schema}.{table}").fetchone()[0]
            print(f"  {schema}.{table}: {count:,} rows")
        con.close()
    except Exception as e:
        print(f"  Could not query row counts: {e}")


def main():
    parser = argparse.ArgumentParser(description="dbt performance benchmarking")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per benchmark (default: 1)")
    args = parser.parse_args()

    print("=" * 55)
    print("  dbt Performance Benchmark")
    print(f"  Runs per benchmark: {args.runs}")
    print("=" * 55)

    start = time.time()
    results = run_benchmark(runs=args.runs)
    total = time.time() - start

    print_summary(results)
    print(f"\n  Total benchmark time: {total:.1f}s")


if __name__ == "__main__":
    main()

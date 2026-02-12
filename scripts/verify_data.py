"""Verify downloaded data by running quick DuckDB queries.

Usage:
    uv run python scripts/verify_data.py
"""
from pathlib import Path

import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
PARQUET = BASE_DIR / "data" / "yellow_tripdata_2024-01.parquet"
ZONES_CSV = BASE_DIR / "nyc_taxi_dbt" / "seeds" / "taxi_zone_lookup.csv"


def main() -> None:
    print("=== Data Verification ===\n")

    con = duckdb.connect()

    # Check parquet
    if PARQUET.exists():
        count = con.execute(
            f"SELECT count(*) FROM read_parquet('{PARQUET}')"
        ).fetchone()[0]
        print(f"Yellow trips (Jan 2024): {count:,} rows")

        print("\nColumn schema:")
        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{PARQUET}')"
        ).fetchall()
        for col_name, col_type, *_ in schema:
            print(f"  {col_name}: {col_type}")

        print("\nFirst 3 rows (sample):")
        rows = con.execute(
            f"SELECT * FROM read_parquet('{PARQUET}') LIMIT 3"
        ).fetchdf()
        print(rows.to_string())
    else:
        print(f"[MISSING] {PARQUET}")
        print("  Run: uv run python scripts/download_data.py")

    # Check zones
    if ZONES_CSV.exists():
        count = con.execute(
            f"SELECT count(*) FROM read_csv_auto('{ZONES_CSV}')"
        ).fetchone()[0]
        print(f"\nTaxi zones: {count} rows")
    else:
        print(f"\n[MISSING] {ZONES_CSV}")
        print("  Run: uv run python scripts/download_data.py")

    con.close()


if __name__ == "__main__":
    main()

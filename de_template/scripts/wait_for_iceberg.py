#!/usr/bin/env python3
"""
wait_for_iceberg.py — Polling gate for Silver Iceberg table readiness.

Runs inside the dbt container (has duckdb Python package via dbt-duckdb).
Polls silver.cleaned_trips via iceberg_scan() until rows > 0 or 90s timeout.

Replaces the brittle 'sleep 15' pattern. Called by: make wait-for-silver
"""
import os
import sys
import time

import duckdb

TIMEOUT_SECONDS = 90
POLL_INTERVAL = 5

endpoint = os.environ.get("DUCKDB_S3_ENDPOINT", "minio:9000")
access_key = os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin")
secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin")
use_ssl = os.environ.get("DUCKDB_S3_USE_SSL", "false").lower() == "true"

SILVER_PATH = "s3://warehouse/silver/cleaned_trips"


def check_silver_count() -> int:
    con = duckdb.connect()
    try:
        con.execute("INSTALL iceberg; INSTALL httpfs; LOAD iceberg; LOAD httpfs;")
        con.execute(f"SET s3_endpoint='{endpoint}';")
        con.execute(f"SET s3_access_key_id='{access_key}';")
        con.execute(f"SET s3_secret_access_key='{secret_key}';")
        con.execute(f"SET s3_use_ssl={'true' if use_ssl else 'false'};")
        con.execute("SET s3_url_style='path';")
        result = con.execute(
            f"SELECT COUNT(*) AS n FROM iceberg_scan('{SILVER_PATH}', allow_moved_paths=true)"
        ).fetchone()
        return result[0] if result else 0
    except Exception:
        return 0
    finally:
        con.close()


deadline = time.time() + TIMEOUT_SECONDS
print(f"Waiting for Silver table: {SILVER_PATH}")
print(f"  S3 endpoint: {endpoint}  |  timeout: {TIMEOUT_SECONDS}s")

while time.time() < deadline:
    count = check_silver_count()
    remaining = int(deadline - time.time())
    if count > 0:
        print(f"  Silver table ready: {count:,} rows ({TIMEOUT_SECONDS - remaining}s elapsed)")
        sys.exit(0)
    print(f"  waiting... ({remaining}s remaining)")
    time.sleep(POLL_INTERVAL)

print(f"\nTIMEOUT: Silver table did not populate within {TIMEOUT_SECONDS}s")
print("  Check Flink Dashboard → Jobs → Exceptions for errors.")
sys.exit(1)

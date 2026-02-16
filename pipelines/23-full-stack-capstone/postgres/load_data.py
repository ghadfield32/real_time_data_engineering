"""Load parquet data into PostgreSQL for CDC capture by Debezium."""
import pyarrow.parquet as pq
import psycopg2
import time
import sys
import os


def wait_for_postgres(host, port, user, password, dbname, max_retries=30):
    """Wait for PostgreSQL to become available."""
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=host, port=port, user=user, password=password, dbname=dbname
            )
            conn.close()
            print(f"PostgreSQL is ready (attempt {i + 1})")
            return True
        except psycopg2.OperationalError:
            print(f"Waiting for PostgreSQL... (attempt {i + 1}/{max_retries})")
            time.sleep(2)
    return False


def main():
    host = os.environ.get("PG_HOST", "postgres")
    port = int(os.environ.get("PG_PORT", 5432))
    user = os.environ.get("PG_USER", "taxi")
    password = os.environ.get("PG_PASSWORD", "taxi")
    dbname = os.environ.get("PG_DB", "taxidb")
    parquet_path = os.environ.get("DATA_PATH", "/data/yellow_tripdata_2024-01.parquet")
    max_rows = int(os.environ.get("MAX_ROWS", "10000"))

    print(f"Waiting for PostgreSQL at {host}:{port}...")
    if not wait_for_postgres(host, port, user, password, dbname):
        print("ERROR: PostgreSQL not available after max retries")
        sys.exit(1)

    print(f"Reading parquet file: {parquet_path}")
    table = pq.read_table(parquet_path)
    df = table.to_pandas()

    if max_rows > 0:
        df = df.head(max_rows)

    print(f"Loading {len(df)} rows into PostgreSQL taxi_trips table...")
    conn = psycopg2.connect(
        host=host, port=port, user=user, password=password, dbname=dbname
    )
    cur = conn.cursor()

    columns = [
        "VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime",
        "passenger_count", "trip_distance", "RatecodeID", "store_and_fwd_flag",
        "PULocationID", "DOLocationID", "payment_type", "fare_amount",
        "extra", "mta_tax", "tip_amount", "tolls_amount",
        "improvement_surcharge", "total_amount", "congestion_surcharge", "Airport_fee"
    ]

    placeholders = ", ".join(["%s"] * len(columns))
    col_names = ", ".join([f'"{c}"' for c in columns])
    insert_sql = f"INSERT INTO taxi_trips ({col_names}) VALUES ({placeholders})"

    batch_size = 1000
    total = len(df)
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = df.iloc[start:end]
        values = []
        for _, row in batch.iterrows():
            row_values = []
            for c in columns:
                val = row[c]
                # Convert pandas NaT/NaN to None for SQL
                if hasattr(val, "isoformat"):
                    row_values.append(val)
                elif str(val) == "nan" or str(val) == "NaT":
                    row_values.append(None)
                else:
                    row_values.append(val)
            values.append(tuple(row_values))
        cur.executemany(insert_sql, values)
        conn.commit()
        print(f"  Loaded {end}/{total} rows...")

    cur.close()
    conn.close()
    print(f"COMPLETE: {total} rows loaded into PostgreSQL taxi_trips table.")


if __name__ == "__main__":
    main()

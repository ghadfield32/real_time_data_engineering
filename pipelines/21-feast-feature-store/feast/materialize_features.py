"""
Export Iceberg Silver data to parquet files for Feast,
then apply feature definitions and materialize to online store.
"""
import os
import duckdb
from datetime import datetime, timedelta


def main():
    print("=== Feast Feature Materialization ===")

    # Connect to DuckDB and read Silver Iceberg data
    con = duckdb.connect()
    con.execute("INSTALL iceberg; LOAD iceberg;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("""
        SET s3_endpoint='minio:9000';
        SET s3_access_key_id='minioadmin';
        SET s3_secret_access_key='minioadmin';
        SET s3_use_ssl=false;
        SET s3_url_style='path';
    """)

    # Export trip features
    print("Exporting trip features...")
    os.makedirs("/app/feast_repo/data", exist_ok=True)
    con.execute("""
        COPY (
            SELECT
                trip_id,
                vendor_id,
                passenger_count,
                trip_distance,
                fare_amount,
                tip_amount,
                total_amount,
                payment_type,
                pickup_location_id,
                dropoff_location_id,
                pickup_datetime
            FROM iceberg_scan('s3://warehouse/silver/cleaned_trips', allow_moved_paths := true)
        ) TO '/app/feast_repo/data/silver_trips.parquet' (FORMAT PARQUET)
    """)
    count = con.execute("""
        SELECT COUNT(*) FROM '/app/feast_repo/data/silver_trips.parquet'
    """).fetchone()[0]
    print(f"  Exported {count} trip records")

    # Export location aggregate features
    print("Exporting location features...")
    con.execute("""
        COPY (
            SELECT
                pickup_location_id,
                AVG(fare_amount) as avg_fare,
                AVG(trip_distance) as avg_trip_distance,
                AVG(CASE WHEN fare_amount > 0 THEN tip_amount / fare_amount * 100 ELSE 0 END) as avg_tip_percentage,
                COUNT(*) as trip_count,
                CURRENT_TIMESTAMP as feature_timestamp
            FROM iceberg_scan('s3://warehouse/silver/cleaned_trips', allow_moved_paths := true)
            GROUP BY pickup_location_id
        ) TO '/app/feast_repo/data/location_features.parquet' (FORMAT PARQUET)
    """)
    loc_count = con.execute("""
        SELECT COUNT(*) FROM '/app/feast_repo/data/location_features.parquet'
    """).fetchone()[0]
    print(f"  Exported {loc_count} location feature records")

    con.close()

    # Apply Feast feature definitions
    print("Applying Feast feature definitions...")
    os.system("cd /app/feast_repo && feast apply")

    # Materialize features to online store
    print("Materializing features to online store...")
    end_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    start_date = "2024-01-01T00:00:00"
    os.system(f"cd /app/feast_repo && feast materialize {start_date} {end_date}")

    print("=== Feature materialization complete ===")


if __name__ == "__main__":
    main()

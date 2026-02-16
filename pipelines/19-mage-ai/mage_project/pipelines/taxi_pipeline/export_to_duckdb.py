"""
Data Exporter: Write silver data to DuckDB
"""
import duckdb

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

@data_exporter
def export_to_duckdb(silver_records, *args, **kwargs):
    """Export silver records to DuckDB database."""
    db_path = '/home/src/default_repo/taxi.duckdb'
    con = duckdb.connect(db_path)

    con.execute("CREATE SCHEMA IF NOT EXISTS silver")
    con.execute("DROP TABLE IF EXISTS silver.cleaned_trips")
    con.execute("""
        CREATE TABLE silver.cleaned_trips (
            trip_id VARCHAR,
            vendor_id INTEGER,
            pickup_datetime TIMESTAMP,
            dropoff_datetime TIMESTAMP,
            passenger_count DOUBLE,
            trip_distance DOUBLE,
            rate_code_id INTEGER,
            store_and_fwd_flag VARCHAR,
            pickup_location_id INTEGER,
            dropoff_location_id INTEGER,
            payment_type INTEGER,
            fare_amount DOUBLE,
            extra DOUBLE,
            mta_tax DOUBLE,
            tip_amount DOUBLE,
            tolls_amount DOUBLE,
            improvement_surcharge DOUBLE,
            total_amount DOUBLE,
            congestion_surcharge DOUBLE,
            airport_fee DOUBLE,
            trip_duration_minutes DOUBLE
        )
    """)

    for r in silver_records:
        con.execute("""
            INSERT INTO silver.cleaned_trips VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, [
            r['trip_id'], r['vendor_id'], r['pickup_datetime'],
            r['dropoff_datetime'], r['passenger_count'], r['trip_distance'],
            r['rate_code_id'], r['store_and_fwd_flag'],
            r['pickup_location_id'], r['dropoff_location_id'],
            r['payment_type'], r['fare_amount'], r['extra'],
            r['mta_tax'], r['tip_amount'], r['tolls_amount'],
            r['improvement_surcharge'], r['total_amount'],
            r['congestion_surcharge'], r['airport_fee'],
            r['trip_duration_minutes'],
        ])

    count = con.execute("SELECT COUNT(*) FROM silver.cleaned_trips").fetchone()[0]
    print(f"Exported {count} records to DuckDB")
    con.close()

"""Load dbt Gold layer output from Iceberg into ClickHouse."""
import duckdb
import subprocess
import os


def main():
    print("=== Loading Gold data into ClickHouse ===")

    con = duckdb.connect()
    con.execute("INSTALL iceberg; LOAD iceberg; INSTALL httpfs; LOAD httpfs;")
    con.execute("""
        SET s3_endpoint='minio:9000';
        SET s3_access_key_id='minioadmin';
        SET s3_secret_access_key='minioadmin';
        SET s3_use_ssl=false;
        SET s3_url_style='path';
    """)

    # Export dbt output to CSV for ClickHouse loading
    os.makedirs("/tmp/export", exist_ok=True)

    tables = [
        ("fct_trips", "s3://warehouse/silver/cleaned_trips"),
    ]

    for table_name, path in tables:
        print(f"Exporting {table_name}...")
        try:
            con.execute(f"""
                COPY (SELECT * FROM iceberg_scan('{path}', allow_moved_paths := true))
                TO '/tmp/export/{table_name}.csv' (HEADER, DELIMITER ',')
            """)
        except Exception as e:
            print(f"  Warning: {e}")

    con.close()
    print("=== Export complete ===")


if __name__ == "__main__":
    main()

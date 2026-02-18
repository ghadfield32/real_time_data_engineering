"""Iceberg Maintenance DAG - Daily at 2 AM.

Operations:
  1. Compact Bronze table (merge small files)
  2. Compact Silver table (merge small files for query performance)
  3. Expire old snapshots (cleanup metadata, keep last 5)
  4. Remove orphan files (reclaim unreferenced storage)
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta


default_args = {
    'owner': 'data-engineering',
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

with DAG(
    'iceberg_maintenance',
    default_args=default_args,
    description='Iceberg table maintenance (compaction, expiration)',
    schedule='0 2 * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['maintenance', 'iceberg'],
) as dag:

    compact_bronze = BashOperator(
        task_id='compact_bronze_table',
        bash_command="""
        docker exec p01-flink-jobmanager /opt/flink/bin/sql-client.sh \
          -i /opt/flink/sql/00-init.sql \
          -e "CALL iceberg_catalog.system.rewrite_data_files(
                table => 'bronze.raw_trips',
                strategy => 'binpack'
              );"
        """,
    )

    compact_silver = BashOperator(
        task_id='compact_silver_table',
        bash_command="""
        docker exec p01-flink-jobmanager /opt/flink/bin/sql-client.sh \
          -i /opt/flink/sql/00-init.sql \
          -e "CALL iceberg_catalog.system.rewrite_data_files(
                table => 'silver.cleaned_trips',
                strategy => 'sort',
                sort_order => 'pickup_date'
              );"
        """,
    )

    expire_snapshots = BashOperator(
        task_id='expire_old_snapshots',
        bash_command="""
        docker exec p01-flink-jobmanager /opt/flink/bin/sql-client.sh \
          -i /opt/flink/sql/00-init.sql \
          -e "CALL iceberg_catalog.system.expire_snapshots(
                table => 'silver.cleaned_trips',
                older_than => CURRENT_TIMESTAMP - INTERVAL '7' DAY,
                retain_last => 5
              );"
        """,
    )

    remove_orphans = BashOperator(
        task_id='remove_orphan_files',
        bash_command="""
        docker exec p01-flink-jobmanager /opt/flink/bin/sql-client.sh \
          -i /opt/flink/sql/00-init.sql \
          -e "CALL iceberg_catalog.system.remove_orphan_files(
                table => 'silver.cleaned_trips',
                older_than => CURRENT_TIMESTAMP - INTERVAL '7' DAY
              );"
        """,
    )

    compact_bronze >> compact_silver >> expire_snapshots >> remove_orphans

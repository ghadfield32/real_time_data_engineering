"""
NYC Taxi Pipeline DAG - Airflow Orchestrated (Pipeline 08)

Orchestrates the Kafka+Flink+Iceberg pipeline with Airflow.
Steps: Create Topics -> Generate Events -> Submit Flink Jobs -> Wait -> dbt Build

NOTE: This DAG runs inside Astronomer (astro dev start) and shells out to
Docker containers on the host via `docker exec` / `docker compose`.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.time_delta import TimeDeltaSensor

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="nyc_taxi_pipeline",
    default_args=default_args,
    description="NYC Taxi streaming pipeline: Kafka -> Flink -> Iceberg -> dbt",
    schedule=None,  # Manual trigger only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["nyc-taxi", "streaming", "benchmark"],
) as dag:

    create_topics = BashOperator(
        task_id="create_kafka_topics",
        bash_command=(
            "docker exec p08-kafka /opt/kafka/bin/kafka-topics.sh "
            "--bootstrap-server localhost:9092 "
            "--create --if-not-exists "
            "--topic taxi.raw_trips --partitions 3 --replication-factor 1"
        ),
    )

    generate_events = BashOperator(
        task_id="generate_events",
        bash_command="docker compose -f /pipelines/docker-compose.yml run --rm data-generator",
    )

    submit_flink_bronze = BashOperator(
        task_id="submit_flink_bronze",
        bash_command=(
            "docker exec -T p08-flink-jobmanager /opt/flink/bin/sql-client.sh embedded "
            "-i /opt/flink/sql/00-init.sql -f /opt/flink/sql/05-bronze.sql"
        ),
    )

    submit_flink_silver = BashOperator(
        task_id="submit_flink_silver",
        bash_command=(
            "docker exec -T p08-flink-jobmanager /opt/flink/bin/sql-client.sh embedded "
            "-i /opt/flink/sql/00-init.sql -f /opt/flink/sql/06-silver.sql"
        ),
    )

    wait_for_processing = TimeDeltaSensor(
        task_id="wait_for_processing",
        delta=timedelta(seconds=60),
        poke_interval=10,
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="docker compose -f /pipelines/docker-compose.yml run --rm dbt build --profiles-dir .",
    )

    # Task dependencies
    create_topics >> generate_events >> submit_flink_bronze >> submit_flink_silver >> wait_for_processing >> dbt_build

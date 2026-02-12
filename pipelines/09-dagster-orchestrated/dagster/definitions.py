"""Dagster definitions for NYC Taxi Pipeline (Pipeline 09)"""
import dagster as dg
import subprocess


@dg.asset(description="Create Kafka topics for taxi data")
def kafka_topics() -> None:
    subprocess.run(
        [
            "docker", "exec", "p09-kafka",
            "/opt/kafka/bin/kafka-topics.sh",
            "--bootstrap-server", "localhost:9092",
            "--create", "--if-not-exists",
            "--topic", "taxi.raw_trips",
            "--partitions", "3", "--replication-factor", "1",
        ],
        check=True,
    )


@dg.asset(deps=[kafka_topics], description="Generate taxi trip events to Kafka")
def generate_events() -> None:
    subprocess.run(
        [
            "docker", "compose", "run", "--rm", "data-generator",
        ],
        check=True,
    )


@dg.asset(deps=[generate_events], description="Submit Flink Bronze + Silver SQL jobs")
def flink_processing() -> None:
    for sql_file in [
        "01-create-kafka-source.sql",
        "02-create-iceberg-catalog.sql",
        "03-bronze-raw-trips.sql",
        "04-silver-cleaned-trips.sql",
    ]:
        subprocess.run(
            [
                "docker", "exec", "-T", "p09-flink-jobmanager",
                "/opt/flink/bin/sql-client.sh", "embedded",
                "-f", f"/opt/flink/sql/{sql_file}",
            ],
            check=True,
        )


@dg.asset(deps=[flink_processing], description="Run dbt build on Silver data")
def dbt_build() -> None:
    import time

    time.sleep(60)  # Wait for Flink processing
    subprocess.run(
        [
            "docker", "compose", "run", "--rm", "dbt",
            "build", "--profiles-dir", ".",
        ],
        check=True,
    )


defs = dg.Definitions(
    assets=[kafka_topics, generate_events, flink_processing, dbt_build],
)

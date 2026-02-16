# =============================================================================
# Pipeline 18: Prefect Flow - NYC Taxi Pipeline
# =============================================================================
# Orchestrates: Kafka topics -> Data generation -> Flink Bronze/Silver -> dbt
# =============================================================================

from prefect import flow, task
from prefect.logging import get_run_logger
import subprocess
import time


@task(name="create-topics", retries=2, retry_delay_seconds=5)
def create_topics():
    """Create Kafka topics for taxi data ingestion."""
    logger = get_run_logger()
    logger.info("Creating Kafka topics...")
    result = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "kafka",
            "/opt/kafka/bin/kafka-topics.sh",
            "--bootstrap-server", "localhost:9092",
            "--create", "--topic", "taxi.raw_trips",
            "--partitions", "3", "--replication-factor", "1",
            "--if-not-exists",
        ],
        capture_output=True,
        text=True,
    )
    logger.info(f"Topics stdout: {result.stdout}")
    if result.returncode != 0:
        logger.error(f"Topics stderr: {result.stderr}")
        raise RuntimeError(f"Failed to create topics: {result.stderr}")
    logger.info("Kafka topics created successfully.")


@task(name="generate-data", retries=1, retry_delay_seconds=10)
def generate_data():
    """Produce taxi trip events to Kafka in burst mode."""
    logger = get_run_logger()
    logger.info("Generating taxi trip data into Kafka...")
    result = subprocess.run(
        ["docker", "compose", "run", "--rm", "data-generator"],
        capture_output=True,
        text=True,
    )
    logger.info(f"Generator stdout: {result.stdout}")
    if result.returncode != 0:
        logger.error(f"Generator stderr: {result.stderr}")
        raise RuntimeError(f"Data generation failed: {result.stderr}")
    logger.info("Data generation complete.")


@task(name="process-bronze", retries=1, retry_delay_seconds=10)
def process_bronze():
    """Submit Flink SQL job for Bronze layer (Kafka -> Iceberg)."""
    logger = get_run_logger()
    logger.info("=== Bronze: Kafka -> Iceberg ===")
    result = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "flink-jobmanager",
            "/opt/flink/bin/sql-client.sh", "embedded",
            "-i", "/opt/flink/sql/00-init.sql",
            "-f", "/opt/flink/sql/05-bronze.sql",
        ],
        capture_output=True,
        text=True,
    )
    logger.info(f"Bronze stdout: {result.stdout}")
    if result.returncode != 0:
        logger.error(f"Bronze stderr: {result.stderr}")
        raise RuntimeError(f"Bronze processing failed: {result.stderr}")
    logger.info("Bronze layer complete.")


@task(name="process-silver", retries=1, retry_delay_seconds=10)
def process_silver():
    """Submit Flink SQL job for Silver layer (Bronze Iceberg -> Silver Iceberg)."""
    logger = get_run_logger()
    logger.info("=== Silver: Bronze -> Cleaned Iceberg ===")
    result = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "flink-jobmanager",
            "/opt/flink/bin/sql-client.sh", "embedded",
            "-i", "/opt/flink/sql/00-init.sql",
            "-f", "/opt/flink/sql/06-silver.sql",
        ],
        capture_output=True,
        text=True,
    )
    logger.info(f"Silver stdout: {result.stdout}")
    if result.returncode != 0:
        logger.error(f"Silver stderr: {result.stderr}")
        raise RuntimeError(f"Silver processing failed: {result.stderr}")
    logger.info("Silver layer complete.")


@task(name="dbt-build", retries=1, retry_delay_seconds=10)
def dbt_build():
    """Run dbt transformations on Iceberg Silver data."""
    logger = get_run_logger()
    logger.info("Running dbt build (full-refresh)...")
    result = subprocess.run(
        [
            "docker", "compose", "run", "--rm", "--entrypoint", "/bin/sh",
            "dbt", "-c",
            "dbt deps --profiles-dir . && dbt build --full-refresh --profiles-dir .",
        ],
        capture_output=True,
        text=True,
    )
    logger.info(f"dbt stdout: {result.stdout}")
    if result.returncode != 0:
        logger.error(f"dbt stderr: {result.stderr}")
        raise RuntimeError(f"dbt build failed: {result.stderr}")
    logger.info("dbt build complete.")


@flow(name="taxi-pipeline", log_prints=True)
def taxi_pipeline():
    """NYC Taxi Pipeline: Kafka -> Flink -> Iceberg -> dbt

    Full end-to-end data pipeline orchestrated by Prefect:
    1. Create Kafka topics
    2. Generate taxi trip data (burst mode)
    3. Process Bronze layer (Kafka -> Iceberg via Flink SQL)
    4. Process Silver layer (Bronze -> Silver Iceberg via Flink SQL)
    5. Run dbt transformations (Silver Iceberg -> DuckDB marts)
    """
    logger = get_run_logger()
    logger.info("============================================================")
    logger.info("  Pipeline 18: Prefect Orchestrated - NYC Taxi Pipeline")
    logger.info("============================================================")

    # Step 1: Create Kafka topics
    create_topics()

    # Step 2: Generate data
    generate_data()

    # Step 3: Wait for data to be available in Kafka
    logger.info("Waiting for Flink processing to catch up...")
    time.sleep(10)

    # Step 4: Process Bronze layer
    process_bronze()

    # Step 5: Process Silver layer
    process_silver()

    # Step 6: Wait for streaming jobs to process data
    logger.info("Waiting for streaming jobs to process data...")
    time.sleep(30)

    # Step 7: Run dbt transformations
    dbt_build()

    logger.info("============================================================")
    logger.info("  Pipeline 18: COMPLETE")
    logger.info("============================================================")


if __name__ == "__main__":
    taxi_pipeline()

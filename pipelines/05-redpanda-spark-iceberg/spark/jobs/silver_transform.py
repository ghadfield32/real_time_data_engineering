"""
Silver Transform: Bronze Iceberg -> Silver Iceberg (Batch)

Reads from Bronze Iceberg `warehouse.bronze.raw_trips` and applies data quality
filters. Writes to Silver Iceberg `warehouse.silver.cleaned_trips` preserving
original column names (VendorID, tpep_pickup_datetime, etc.) so that the dbt
staging layer (stg_yellow_trips.sql) can apply the canonical rename + type casts.

Architecture note: this pipeline (P05) uses dbt-duckdb reading Iceberg via
iceberg_scan(), the same pattern as P04 (Flink). Spark's role is Bronze ingest +
quality filtering; dbt handles all renaming, casting, and derived metrics.

Filters applied (matching stg_yellow_trips.sql WHERE clause):
  - Null pickup/dropoff datetimes excluded
  - trip_distance >= 0
  - fare_amount >= 0
  - pickup date within January 2024 (data quality: ~18 out-of-range rows)
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import TimestampType


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("Pipeline05_SilverTransform")
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        )
        .config("spark.sql.catalog.warehouse", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.warehouse.type", "hadoop")
        .config("spark.sql.catalog.warehouse.warehouse", "s3a://warehouse/iceberg")
        .config(
            "spark.sql.catalog.warehouse.io-impl",
            "org.apache.iceberg.aws.s3.S3FileIO",
        )
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate()
    )


def ensure_silver_table(spark: SparkSession) -> None:
    """Create Silver namespace and table if they do not exist.

    Column names match the Bronze table (original Parquet names). dbt's
    stg_yellow_trips.sql performs the rename to snake_case at query time.
    """
    spark.sql("CREATE NAMESPACE IF NOT EXISTS warehouse.silver")
    spark.sql("""
        CREATE TABLE IF NOT EXISTS warehouse.silver.cleaned_trips (
            VendorID                BIGINT,
            tpep_pickup_datetime    TIMESTAMP,
            tpep_dropoff_datetime   TIMESTAMP,
            passenger_count         DOUBLE,
            trip_distance           DOUBLE,
            RatecodeID              DOUBLE,
            store_and_fwd_flag      STRING,
            PULocationID            BIGINT,
            DOLocationID            BIGINT,
            payment_type            BIGINT,
            fare_amount             DOUBLE,
            extra                   DOUBLE,
            mta_tax                 DOUBLE,
            tip_amount              DOUBLE,
            tolls_amount            DOUBLE,
            improvement_surcharge   DOUBLE,
            total_amount            DOUBLE,
            congestion_surcharge    DOUBLE,
            Airport_fee             DOUBLE
        ) USING iceberg
    """)
    print("Silver table warehouse.silver.cleaned_trips is ready.")


def run_silver_transform(spark: SparkSession) -> None:
    """Read Bronze, apply quality filters, write Silver with original column names."""

    bronze_df = spark.table("warehouse.bronze.raw_trips")
    bronze_count = bronze_df.count()
    print(f"Bronze rows read: {bronze_count:,}")

    silver_df = (
        bronze_df
        .withColumn(
            "tpep_pickup_datetime",
            F.to_timestamp(F.col("tpep_pickup_datetime")).cast(TimestampType()),
        )
        .withColumn(
            "tpep_dropoff_datetime",
            F.to_timestamp(F.col("tpep_dropoff_datetime")).cast(TimestampType()),
        )
        .filter(F.col("tpep_pickup_datetime").isNotNull())
        .filter(F.col("tpep_dropoff_datetime").isNotNull())
        .filter(F.col("trip_distance") >= 0)
        .filter(F.col("fare_amount") >= 0)
        .filter(F.col("tpep_pickup_datetime").cast("date") >= F.lit("2024-01-01"))
        .filter(F.col("tpep_pickup_datetime").cast("date") < F.lit("2024-02-01"))
        .select(
            F.col("VendorID"),
            F.col("tpep_pickup_datetime"),
            F.col("tpep_dropoff_datetime"),
            F.col("passenger_count"),
            F.col("trip_distance"),
            F.col("RatecodeID"),
            F.col("store_and_fwd_flag"),
            F.col("PULocationID"),
            F.col("DOLocationID"),
            F.col("payment_type"),
            F.col("fare_amount"),
            F.col("extra"),
            F.col("mta_tax"),
            F.col("tip_amount"),
            F.col("tolls_amount"),
            F.col("improvement_surcharge"),
            F.col("total_amount"),
            F.col("congestion_surcharge"),
            F.col("Airport_fee"),
        )
    )

    silver_df.writeTo("warehouse.silver.cleaned_trips").overwritePartitions()

    silver_count = spark.table("warehouse.silver.cleaned_trips").count()
    filtered = bronze_count - silver_count
    print(f"Silver transform complete. Rows written: {silver_count:,}")
    print(f"Rows filtered out: {filtered:,}")


def main():
    print("=" * 60)
    print("  Pipeline 05 — Silver Transform (Bronze -> Silver Iceberg)")
    print("  Column names preserved for dbt-duckdb consumption")
    print("=" * 60)

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    try:
        ensure_silver_table(spark)
        run_silver_transform(spark)
    finally:
        spark.stop()

    print("=" * 60)
    print("  Silver Transform COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

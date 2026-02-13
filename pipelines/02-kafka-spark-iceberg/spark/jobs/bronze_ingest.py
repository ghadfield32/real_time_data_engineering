"""
Bronze Ingest: Kafka -> Iceberg (Structured Streaming)

Reads raw taxi trip JSON events from the Kafka topic `taxi.raw_trips`,
parses the JSON value column, and writes to the Bronze Iceberg table
`warehouse.bronze.raw_trips` in append mode.

Uses trigger(availableNow=True) for benchmark mode: process all available
messages then stop the streaming query.

Usage:
    spark-submit --packages ... bronze_ingest.py
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    IntegerType,
    LongType,
    DoubleType,
    StringType,
    TimestampType,
)


def get_taxi_schema() -> StructType:
    """Define the JSON schema matching the taxi trip event format."""
    return StructType([
        StructField("VendorID", IntegerType(), True),
        StructField("tpep_pickup_datetime", StringType(), True),
        StructField("tpep_dropoff_datetime", StringType(), True),
        StructField("passenger_count", IntegerType(), True),
        StructField("trip_distance", DoubleType(), True),
        StructField("RatecodeID", IntegerType(), True),
        StructField("store_and_fwd_flag", StringType(), True),
        StructField("PULocationID", IntegerType(), True),
        StructField("DOLocationID", IntegerType(), True),
        StructField("payment_type", IntegerType(), True),
        StructField("fare_amount", DoubleType(), True),
        StructField("extra", DoubleType(), True),
        StructField("mta_tax", DoubleType(), True),
        StructField("tip_amount", DoubleType(), True),
        StructField("tolls_amount", DoubleType(), True),
        StructField("improvement_surcharge", DoubleType(), True),
        StructField("total_amount", DoubleType(), True),
        StructField("congestion_surcharge", DoubleType(), True),
        StructField("Airport_fee", DoubleType(), True),
    ])


def create_spark_session() -> SparkSession:
    """Create a Spark session with Iceberg catalog configuration."""
    return (
        SparkSession.builder
        .appName("Pipeline02_BronzeIngest")
        # Iceberg extensions and catalog are set via spark-defaults.conf
        # or via --conf flags at spark-submit time. We reinforce them here
        # for standalone clarity.
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


def ensure_bronze_table(spark: SparkSession) -> None:
    """Create the Bronze namespace and table if they do not exist."""
    spark.sql("CREATE NAMESPACE IF NOT EXISTS warehouse.bronze")
    spark.sql("""
        CREATE TABLE IF NOT EXISTS warehouse.bronze.raw_trips (
            VendorID                INT,
            tpep_pickup_datetime    TIMESTAMP,
            tpep_dropoff_datetime   TIMESTAMP,
            passenger_count         INT,
            trip_distance           DOUBLE,
            RatecodeID              INT,
            store_and_fwd_flag      STRING,
            PULocationID            INT,
            DOLocationID            INT,
            payment_type            INT,
            fare_amount             DOUBLE,
            extra                   DOUBLE,
            mta_tax                 DOUBLE,
            tip_amount              DOUBLE,
            tolls_amount            DOUBLE,
            improvement_surcharge   DOUBLE,
            total_amount            DOUBLE,
            congestion_surcharge    DOUBLE,
            Airport_fee             DOUBLE,
            kafka_timestamp         TIMESTAMP,
            kafka_partition         INT,
            kafka_offset            LONG
        ) USING iceberg
    """)
    print("Bronze table warehouse.bronze.raw_trips is ready.")


def run_bronze_ingest(spark: SparkSession) -> None:
    """Read from Kafka, parse JSON, and write to Bronze Iceberg table."""

    taxi_schema = get_taxi_schema()

    # -------------------------------------------------------------------------
    # Read from Kafka
    # -------------------------------------------------------------------------
    kafka_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("subscribe", "taxi.raw_trips")
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .load()
    )

    # -------------------------------------------------------------------------
    # Parse JSON value and extract Kafka metadata
    # -------------------------------------------------------------------------
    parsed_df = (
        kafka_df
        .select(
            F.from_json(F.col("value").cast("string"), taxi_schema).alias("data"),
            F.col("timestamp").alias("kafka_timestamp"),
            F.col("partition").alias("kafka_partition"),
            F.col("offset").alias("kafka_offset"),
        )
        .select(
            # Taxi fields
            F.col("data.VendorID"),
            F.to_timestamp(F.col("data.tpep_pickup_datetime")).alias("tpep_pickup_datetime"),
            F.to_timestamp(F.col("data.tpep_dropoff_datetime")).alias("tpep_dropoff_datetime"),
            F.col("data.passenger_count"),
            F.col("data.trip_distance"),
            F.col("data.RatecodeID"),
            F.col("data.store_and_fwd_flag"),
            F.col("data.PULocationID"),
            F.col("data.DOLocationID"),
            F.col("data.payment_type"),
            F.col("data.fare_amount"),
            F.col("data.extra"),
            F.col("data.mta_tax"),
            F.col("data.tip_amount"),
            F.col("data.tolls_amount"),
            F.col("data.improvement_surcharge"),
            F.col("data.total_amount"),
            F.col("data.congestion_surcharge"),
            F.col("data.Airport_fee"),
            # Kafka metadata
            F.col("kafka_timestamp"),
            F.col("kafka_partition"),
            F.col("kafka_offset"),
        )
    )

    # -------------------------------------------------------------------------
    # Write to Iceberg in append mode (availableNow for benchmark)
    # -------------------------------------------------------------------------
    query = (
        parsed_df.writeStream
        .format("iceberg")
        .outputMode("append")
        .option("checkpointLocation", "s3a://warehouse/checkpoints/bronze_ingest")
        .trigger(availableNow=True)
        .toTable("warehouse.bronze.raw_trips")
    )

    # Wait for the streaming query to finish processing all available data
    query.awaitTermination()

    # Report row count
    count = spark.table("warehouse.bronze.raw_trips").count()
    print(f"Bronze ingest complete. Total rows in warehouse.bronze.raw_trips: {count:,}")


def main():
    print("=" * 60)
    print("  Pipeline 02 — Bronze Ingest (Kafka -> Iceberg)")
    print("=" * 60)

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    try:
        ensure_bronze_table(spark)
        run_bronze_ingest(spark)
    finally:
        spark.stop()

    print("=" * 60)
    print("  Bronze Ingest COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

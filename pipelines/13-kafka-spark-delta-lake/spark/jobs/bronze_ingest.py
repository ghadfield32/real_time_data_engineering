"""Bronze Ingest: Kafka -> Delta Lake on MinIO (Structured Streaming).

Reads raw NYC Yellow Taxi trip events from Kafka topic 'taxi.raw_trips',
parses the JSON payloads, and writes them as a Delta Lake table to MinIO
(Bronze layer: raw events with ingestion timestamp).
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp
from pyspark.sql.types import (
    StructType, StructField, IntegerType, DoubleType, StringType,
)


def main():
    spark = (
        SparkSession.builder
        .appName("P13-Bronze-Ingest-Delta")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate()
    )

    # Schema matching the NYC Yellow Taxi data generator output
    schema = StructType([
        StructField("VendorID", IntegerType()),
        StructField("tpep_pickup_datetime", StringType()),
        StructField("tpep_dropoff_datetime", StringType()),
        StructField("passenger_count", DoubleType()),
        StructField("trip_distance", DoubleType()),
        StructField("RatecodeID", DoubleType()),
        StructField("store_and_fwd_flag", StringType()),
        StructField("PULocationID", IntegerType()),
        StructField("DOLocationID", IntegerType()),
        StructField("payment_type", IntegerType()),
        StructField("fare_amount", DoubleType()),
        StructField("extra", DoubleType()),
        StructField("mta_tax", DoubleType()),
        StructField("tip_amount", DoubleType()),
        StructField("tolls_amount", DoubleType()),
        StructField("improvement_surcharge", DoubleType()),
        StructField("total_amount", DoubleType()),
        StructField("congestion_surcharge", DoubleType()),
        StructField("Airport_fee", DoubleType()),
    ])

    # Read from Kafka
    kafka_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("subscribe", "taxi.raw_trips")
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .load()
    )

    # Parse JSON values and flatten
    parsed_df = (
        kafka_df
        .selectExpr("CAST(value AS STRING) as json_str")
        .select(from_json(col("json_str"), schema).alias("data"))
        .select("data.*")
        .withColumn("ingested_at", current_timestamp())
    )

    bronze_path = "s3a://warehouse/bronze/raw_trips"

    # Write to Delta Lake on MinIO using availableNow trigger
    # (processes all available data then stops)
    query = (
        parsed_df.writeStream
        .format("delta")
        .outputMode("append")
        .option("checkpointLocation", "s3a://warehouse/checkpoints/bronze_ingest")
        .trigger(availableNow=True)
        .start(bronze_path)
    )
    query.awaitTermination()

    # Report results
    count = spark.read.format("delta").load(bronze_path).count()
    print(f"Bronze ingest complete. Total rows in Delta table: {count:,}")
    print("=" * 60)
    print("  Bronze Ingest COMPLETE")
    print("=" * 60)
    spark.stop()


if __name__ == "__main__":
    main()

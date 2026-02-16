"""Bronze Ingest: Kafka -> Hudi on MinIO (Structured Streaming).

Reads raw NYC Yellow Taxi trip events from Kafka topic 'taxi.raw_trips',
parses the JSON payloads, and writes them as a Hudi Copy-on-Write table
to MinIO (Bronze layer: raw events with ingestion timestamp).

Hudi is optimized for CDC and upsert workloads, using a composite record
key (VendorID + pickup_datetime + PULocationID) with ingested_at as the
precombine field for deduplication.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp
from pyspark.sql.types import (
    StructType, StructField, IntegerType, DoubleType, StringType,
)
import os


def main():
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka:9092")
    s3_endpoint = os.getenv("S3_ENDPOINT", "http://minio:9000")

    spark = (
        SparkSession.builder
        .appName("P22-Bronze-Ingest-Hudi")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.hudi.catalog.HoodieCatalog",
        )
        .config(
            "spark.sql.extensions",
            "org.apache.spark.sql.hudi.HoodieSparkSessionExtension",
        )
        .config("spark.hadoop.fs.s3a.endpoint", s3_endpoint)
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
        .option("kafka.bootstrap.servers", kafka_broker)
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

    # Write to Hudi Copy-on-Write table on MinIO using availableNow trigger
    # (processes all available data then stops)
    query = (
        parsed_df.writeStream
        .format("hudi")
        .option("hoodie.table.name", "bronze_raw_trips")
        .option("hoodie.datasource.write.table.type", "COPY_ON_WRITE")
        .option("hoodie.datasource.write.recordkey.field",
                "VendorID,tpep_pickup_datetime,PULocationID")
        .option("hoodie.datasource.write.precombine.field", "ingested_at")
        .option("hoodie.datasource.write.operation", "insert")
        .option("hoodie.datasource.write.partitionpath.field", "")
        .option("path", bronze_path)
        .option("checkpointLocation", "s3a://warehouse/checkpoints/bronze")
        .trigger(availableNow=True)
        .start()
    )
    query.awaitTermination()

    # Report results
    count = spark.read.format("hudi").load(bronze_path).count()
    print(f"Bronze ingest complete. Total rows in Hudi table: {count:,}")
    print("=" * 60)
    print("  Bronze Ingest (Hudi COW) COMPLETE")
    print("=" * 60)
    spark.stop()


if __name__ == "__main__":
    main()

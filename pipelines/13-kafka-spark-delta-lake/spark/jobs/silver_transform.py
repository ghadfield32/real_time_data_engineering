"""Silver Transform: Bronze Delta Lake -> Silver Delta Lake.

Reads the Bronze layer Delta table (raw events), applies data quality
filters, renames columns to snake_case, generates a trip_id surrogate key,
and writes to a Silver layer Delta table.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, to_timestamp, md5, concat_ws, lit, round as spark_round,
)


def main():
    spark = (
        SparkSession.builder
        .appName("P13-Silver-Transform-Delta")
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

    bronze_path = "s3a://warehouse/bronze/raw_trips"
    silver_path = "s3a://warehouse/silver/cleaned_trips"

    # Read Bronze Delta table
    bronze_df = spark.read.format("delta").load(bronze_path)
    bronze_count = bronze_df.count()
    print(f"Bronze rows read: {bronze_count:,}")

    # Apply quality filters and transformations
    silver_df = (
        bronze_df
        # Parse timestamps from string
        .withColumn("pickup_datetime", to_timestamp(col("tpep_pickup_datetime")))
        .withColumn("dropoff_datetime", to_timestamp(col("tpep_dropoff_datetime")))
        # Quality filters
        .filter(col("pickup_datetime").isNotNull())
        .filter(col("dropoff_datetime").isNotNull())
        .filter(col("trip_distance") >= 0)
        .filter(col("fare_amount") >= 0)
        .filter(col("pickup_datetime") >= lit("2024-01-01"))
        # Generate surrogate key
        .withColumn(
            "trip_id",
            md5(concat_ws(
                "|",
                col("VendorID").cast("string"),
                col("tpep_pickup_datetime"),
                col("tpep_dropoff_datetime"),
                col("PULocationID").cast("string"),
                col("DOLocationID").cast("string"),
                col("fare_amount").cast("string"),
                col("total_amount").cast("string"),
            )),
        )
        # Select and rename to snake_case
        .select(
            col("trip_id"),
            col("VendorID").alias("vendor_id").cast("int"),
            col("pickup_datetime"),
            col("dropoff_datetime"),
            col("passenger_count").cast("double"),
            col("trip_distance").alias("trip_distance_miles").cast("double"),
            col("RatecodeID").alias("rate_code_id").cast("int"),
            col("store_and_fwd_flag"),
            col("PULocationID").alias("pickup_location_id").cast("int"),
            col("DOLocationID").alias("dropoff_location_id").cast("int"),
            col("payment_type").cast("int"),
            spark_round(col("fare_amount"), 2).alias("fare_amount"),
            spark_round(col("extra"), 2).alias("extra"),
            spark_round(col("mta_tax"), 2).alias("mta_tax"),
            spark_round(col("tip_amount"), 2).alias("tip_amount"),
            spark_round(col("tolls_amount"), 2).alias("tolls_amount"),
            spark_round(col("improvement_surcharge"), 2).alias("improvement_surcharge"),
            spark_round(col("total_amount"), 2).alias("total_amount"),
            spark_round(col("congestion_surcharge"), 2).alias("congestion_surcharge"),
            spark_round(col("Airport_fee"), 2).alias("airport_fee"),
        )
    )

    # Write to Silver Delta table (overwrite for batch re-processing)
    silver_df.write.format("delta").mode("overwrite").save(silver_path)

    # Report results
    silver_count = spark.read.format("delta").load(silver_path).count()
    filtered = bronze_count - silver_count
    print(f"Silver transform complete. Rows written: {silver_count:,}")
    print(f"Rows filtered out: {filtered:,}")
    print("=" * 60)
    print("  Silver Transform COMPLETE")
    print("=" * 60)
    spark.stop()


if __name__ == "__main__":
    main()

"""
Silver Transform: Bronze Iceberg -> Silver Iceberg (Batch)

Reads from the Bronze Iceberg table `warehouse.bronze.raw_trips` and applies
transformations matching the shared dbt models (stg_yellow_trips.sql +
int_trip_metrics.sql):

  1. Rename columns (VendorID -> vendor_id, etc.)
  2. Cast types
  3. Filter nulls, negative fares, date range
  4. Generate surrogate key: md5(concat_ws('|', ...))
  5. Compute derived metrics:
     - duration_minutes
     - avg_speed_mph
     - cost_per_mile
     - tip_percentage
  6. Add time dimensions: pickup_date, pickup_hour, pickup_day_of_week, is_weekend
  7. Filter impossible trips (duration < 1 or > 720, speed > 100)

Writes to Silver Iceberg table `warehouse.silver.cleaned_trips` in overwrite mode.

Usage:
    spark-submit --packages ... silver_transform.py
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DecimalType,
    DoubleType,
    IntegerType,
    TimestampType,
)


def create_spark_session() -> SparkSession:
    """Create a Spark session with Iceberg catalog configuration."""
    return (
        SparkSession.builder
        .appName("Pipeline02_SilverTransform")
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        )
        .config("spark.sql.catalog.warehouse", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.warehouse.type", "hadoop")
        .config("spark.sql.catalog.warehouse.warehouse", "s3a://warehouse/")
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
    """Create the Silver namespace and table if they do not exist."""
    spark.sql("CREATE NAMESPACE IF NOT EXISTS warehouse.silver")
    spark.sql("""
        CREATE TABLE IF NOT EXISTS warehouse.silver.cleaned_trips (
            trip_id                  STRING,
            vendor_id                INT,
            rate_code_id             INT,
            pickup_location_id       INT,
            dropoff_location_id      INT,
            payment_type_id          INT,
            pickup_datetime          TIMESTAMP,
            dropoff_datetime         TIMESTAMP,
            passenger_count          INT,
            trip_distance_miles      DOUBLE,
            store_and_fwd_flag       STRING,
            fare_amount              DECIMAL(10, 2),
            extra_amount             DECIMAL(10, 2),
            mta_tax                  DECIMAL(10, 2),
            tip_amount               DECIMAL(10, 2),
            tolls_amount             DECIMAL(10, 2),
            improvement_surcharge    DECIMAL(10, 2),
            total_amount             DECIMAL(10, 2),
            congestion_surcharge     DECIMAL(10, 2),
            airport_fee              DECIMAL(10, 2),
            trip_duration_minutes    LONG,
            avg_speed_mph            DOUBLE,
            cost_per_mile            DOUBLE,
            tip_percentage           DOUBLE,
            pickup_date              DATE,
            pickup_hour              INT,
            pickup_day_of_week       STRING,
            is_weekend               BOOLEAN
        ) USING iceberg
    """)
    print("Silver table warehouse.silver.cleaned_trips is ready.")


def run_silver_transform(spark: SparkSession) -> None:
    """Read Bronze table, apply staging + metric transformations, write Silver."""

    # -------------------------------------------------------------------------
    # 1. Read Bronze
    # -------------------------------------------------------------------------
    bronze_df = spark.table("warehouse.bronze.raw_trips")
    bronze_count = bronze_df.count()
    print(f"Bronze rows read: {bronze_count:,}")

    # -------------------------------------------------------------------------
    # 2. Staging: rename, cast, filter (matches stg_yellow_trips.sql)
    # -------------------------------------------------------------------------
    staged_df = (
        bronze_df
        .select(
            # Identifiers — rename and cast
            F.col("VendorID").cast(IntegerType()).alias("vendor_id"),
            F.col("RatecodeID").cast(IntegerType()).alias("rate_code_id"),
            F.col("PULocationID").cast(IntegerType()).alias("pickup_location_id"),
            F.col("DOLocationID").cast(IntegerType()).alias("dropoff_location_id"),
            F.col("payment_type").cast(IntegerType()).alias("payment_type_id"),

            # Timestamps
            F.col("tpep_pickup_datetime").cast(TimestampType()).alias("pickup_datetime"),
            F.col("tpep_dropoff_datetime").cast(TimestampType()).alias("dropoff_datetime"),

            # Trip info
            F.col("passenger_count").cast(IntegerType()).alias("passenger_count"),
            F.col("trip_distance").cast(DoubleType()).alias("trip_distance_miles"),
            F.col("store_and_fwd_flag"),

            # Financials — cast to decimal(10,2) with rounding
            F.round(F.col("fare_amount").cast(DecimalType(10, 2)), 2).alias("fare_amount"),
            F.round(F.col("extra").cast(DecimalType(10, 2)), 2).alias("extra_amount"),
            F.round(F.col("mta_tax").cast(DecimalType(10, 2)), 2).alias("mta_tax"),
            F.round(F.col("tip_amount").cast(DecimalType(10, 2)), 2).alias("tip_amount"),
            F.round(F.col("tolls_amount").cast(DecimalType(10, 2)), 2).alias("tolls_amount"),
            F.round(
                F.col("improvement_surcharge").cast(DecimalType(10, 2)), 2
            ).alias("improvement_surcharge"),
            F.round(F.col("total_amount").cast(DecimalType(10, 2)), 2).alias("total_amount"),
            F.round(
                F.col("congestion_surcharge").cast(DecimalType(10, 2)), 2
            ).alias("congestion_surcharge"),
            F.round(F.col("Airport_fee").cast(DecimalType(10, 2)), 2).alias("airport_fee"),
        )
        # Basic quality filters (matching stg_yellow_trips.sql WHERE clause)
        .filter(F.col("pickup_datetime").isNotNull())
        .filter(F.col("dropoff_datetime").isNotNull())
        .filter(F.col("trip_distance_miles") >= 0)
        .filter(F.col("fare_amount") >= 0)
        # Date range filter: January 2024 only
        .filter(F.col("pickup_datetime").cast("date") >= F.lit("2024-01-01"))
        .filter(F.col("pickup_datetime").cast("date") < F.lit("2024-02-01"))
    )

    # -------------------------------------------------------------------------
    # 3. Generate surrogate key: md5(concat_ws('|', ...))
    #    Matches dbt_utils.generate_surrogate_key logic
    # -------------------------------------------------------------------------
    staged_with_key = staged_df.withColumn(
        "trip_id",
        F.md5(
            F.concat_ws(
                "|",
                F.coalesce(F.col("vendor_id").cast("string"), F.lit("")),
                F.coalesce(F.col("pickup_datetime").cast("string"), F.lit("")),
                F.coalesce(F.col("dropoff_datetime").cast("string"), F.lit("")),
                F.coalesce(F.col("pickup_location_id").cast("string"), F.lit("")),
                F.coalesce(F.col("dropoff_location_id").cast("string"), F.lit("")),
                F.coalesce(F.col("fare_amount").cast("string"), F.lit("")),
                F.coalesce(F.col("total_amount").cast("string"), F.lit("")),
            )
        ),
    )

    # -------------------------------------------------------------------------
    # 4. Compute derived metrics (matches int_trip_metrics.sql)
    # -------------------------------------------------------------------------
    enriched_df = (
        staged_with_key
        # Duration in minutes: (unix_ts(dropoff) - unix_ts(pickup)) / 60
        .withColumn(
            "trip_duration_minutes",
            (
                (F.unix_timestamp("dropoff_datetime") - F.unix_timestamp("pickup_datetime"))
                / 60
            ).cast("long"),
        )
        # Average speed: distance / (duration / 60)
        .withColumn(
            "avg_speed_mph",
            F.when(
                F.col("trip_duration_minutes") > 0,
                F.round(
                    F.col("trip_distance_miles") / (F.col("trip_duration_minutes") / 60.0),
                    2,
                ),
            ).otherwise(F.lit(None)),
        )
        # Cost per mile
        .withColumn(
            "cost_per_mile",
            F.when(
                F.col("trip_distance_miles") > 0,
                F.round(F.col("fare_amount") / F.col("trip_distance_miles"), 2),
            ).otherwise(F.lit(None)),
        )
        # Tip percentage
        .withColumn(
            "tip_percentage",
            F.when(
                F.col("fare_amount") > 0,
                F.round((F.col("tip_amount") / F.col("fare_amount")) * 100, 2),
            ).otherwise(F.lit(None)),
        )
        # Time dimensions
        .withColumn("pickup_date", F.to_date("pickup_datetime"))
        .withColumn("pickup_hour", F.hour("pickup_datetime").cast(IntegerType()))
        .withColumn("pickup_day_of_week", F.date_format("pickup_datetime", "EEEE"))
        .withColumn(
            "is_weekend",
            F.dayofweek("pickup_datetime").isin([1, 7]),  # Spark: 1=Sun, 7=Sat
        )
    )

    # -------------------------------------------------------------------------
    # 5. Filter impossible trips (matches int_trip_metrics.sql WHERE clause)
    # -------------------------------------------------------------------------
    silver_df = (
        enriched_df
        .filter(
            (F.col("trip_duration_minutes") >= 1) & (F.col("trip_duration_minutes") <= 720)
        )
        .filter(
            F.col("avg_speed_mph").isNull() | (F.col("avg_speed_mph") < 100)
        )
    )

    # -------------------------------------------------------------------------
    # 6. Select final columns in correct order and write to Silver
    # -------------------------------------------------------------------------
    final_df = silver_df.select(
        "trip_id",
        "vendor_id",
        "rate_code_id",
        "pickup_location_id",
        "dropoff_location_id",
        "payment_type_id",
        "pickup_datetime",
        "dropoff_datetime",
        "passenger_count",
        "trip_distance_miles",
        "store_and_fwd_flag",
        "fare_amount",
        "extra_amount",
        "mta_tax",
        "tip_amount",
        "tolls_amount",
        "improvement_surcharge",
        "total_amount",
        "congestion_surcharge",
        "airport_fee",
        "trip_duration_minutes",
        "avg_speed_mph",
        "cost_per_mile",
        "tip_percentage",
        "pickup_date",
        "pickup_hour",
        "pickup_day_of_week",
        "is_weekend",
    )

    # Write to Silver Iceberg table (overwrite mode)
    final_df.writeTo("warehouse.silver.cleaned_trips").overwritePartitions()

    silver_count = spark.table("warehouse.silver.cleaned_trips").count()
    print(f"Silver transform complete. Rows written: {silver_count:,}")
    print(f"Rows filtered out: {bronze_count - silver_count:,}")


def main():
    print("=" * 60)
    print("  Pipeline 02 — Silver Transform (Bronze -> Silver Iceberg)")
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

-- =============================================================================
-- Pipeline 04: Silver Layer (Bronze Iceberg → Silver Iceberg)
-- =============================================================================
-- Run: sql-client.sh embedded -i 00-init.sql -f 06-silver.sql
-- =============================================================================

USE CATALOG iceberg_catalog;
CREATE DATABASE IF NOT EXISTS silver;

CREATE TABLE IF NOT EXISTS silver.cleaned_trips (
    trip_id                 STRING,
    vendor_id               INT,
    rate_code_id            INT,
    pickup_location_id      INT,
    dropoff_location_id     INT,
    payment_type_id         INT,
    pickup_datetime         TIMESTAMP(3),
    dropoff_datetime        TIMESTAMP(3),
    passenger_count         INT,
    trip_distance_miles     DOUBLE,
    store_and_fwd_flag      STRING,
    fare_amount             DECIMAL(10, 2),
    extra_amount            DECIMAL(10, 2),
    mta_tax                 DECIMAL(10, 2),
    tip_amount              DECIMAL(10, 2),
    tolls_amount            DECIMAL(10, 2),
    improvement_surcharge   DECIMAL(10, 2),
    total_amount            DECIMAL(10, 2),
    congestion_surcharge    DECIMAL(10, 2),
    airport_fee             DECIMAL(10, 2),
    pickup_date             DATE
) PARTITIONED BY (pickup_date)
WITH (
    'format-version' = '2',
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'zstd',
    'write.metadata.delete-after-commit.enabled' = 'true',
    'write.metadata.previous-versions-max' = '10',
    'write.target-file-size-bytes' = '134217728'
);

-- Deduplication: ROW_NUMBER partitioned by natural key, keeping latest ingestion
INSERT INTO iceberg_catalog.silver.cleaned_trips
WITH deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY VendorID, tpep_pickup_datetime, tpep_dropoff_datetime,
                         PULocationID, DOLocationID, fare_amount, total_amount
            ORDER BY ingestion_ts DESC
        ) AS rn
    FROM iceberg_catalog.bronze.raw_trips
    WHERE tpep_pickup_datetime IS NOT NULL
      AND tpep_dropoff_datetime IS NOT NULL
      AND trip_distance >= 0
      AND fare_amount >= 0
      AND CAST(tpep_pickup_datetime AS DATE) >= DATE '2024-01-01'
      AND CAST(tpep_pickup_datetime AS DATE) <  DATE '2024-02-01'
)
SELECT
    CAST(MD5(CONCAT_WS('|',
        CAST(VendorID AS STRING),
        CAST(tpep_pickup_datetime AS STRING),
        CAST(tpep_dropoff_datetime AS STRING),
        CAST(PULocationID AS STRING),
        CAST(DOLocationID AS STRING),
        CAST(fare_amount AS STRING),
        CAST(total_amount AS STRING)
    )) AS STRING) AS trip_id,
    CAST(VendorID AS INT)       AS vendor_id,
    CAST(RatecodeID AS INT)     AS rate_code_id,
    CAST(PULocationID AS INT)   AS pickup_location_id,
    CAST(DOLocationID AS INT)   AS dropoff_location_id,
    CAST(payment_type AS INT)   AS payment_type_id,
    tpep_pickup_datetime        AS pickup_datetime,
    tpep_dropoff_datetime       AS dropoff_datetime,
    CAST(passenger_count AS INT) AS passenger_count,
    trip_distance               AS trip_distance_miles,
    store_and_fwd_flag,
    CAST(ROUND(fare_amount, 2)             AS DECIMAL(10, 2)) AS fare_amount,
    CAST(ROUND(extra, 2)                   AS DECIMAL(10, 2)) AS extra_amount,
    CAST(ROUND(mta_tax, 2)                 AS DECIMAL(10, 2)) AS mta_tax,
    CAST(ROUND(tip_amount, 2)              AS DECIMAL(10, 2)) AS tip_amount,
    CAST(ROUND(tolls_amount, 2)            AS DECIMAL(10, 2)) AS tolls_amount,
    CAST(ROUND(improvement_surcharge, 2)   AS DECIMAL(10, 2)) AS improvement_surcharge,
    CAST(ROUND(total_amount, 2)            AS DECIMAL(10, 2)) AS total_amount,
    CAST(ROUND(congestion_surcharge, 2)    AS DECIMAL(10, 2)) AS congestion_surcharge,
    CAST(ROUND(Airport_fee, 2)             AS DECIMAL(10, 2)) AS airport_fee,
    CAST(tpep_pickup_datetime AS DATE) AS pickup_date
FROM deduped
WHERE rn = 1;

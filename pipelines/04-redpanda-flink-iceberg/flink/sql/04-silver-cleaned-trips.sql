-- =============================================================================
-- Pipeline 04: Flink SQL - Silver Layer (Cleaned Trips)
-- =============================================================================
-- Creates the Silver Iceberg table and starts a continuous INSERT job
-- that reads from the Bronze table, applies data quality filters,
-- renames columns to snake_case, and computes enrichment columns.
--
-- Silver layer transformations:
--   1. Column renaming (VendorID -> vendor_id, PULocationID -> pickup_location_id, etc.)
--   2. Type casting (BIGINT -> INT where appropriate)
--   3. Data quality filters:
--      - Reject null timestamps
--      - Reject negative fare amounts and trip distances
--      - Reject pickup dates outside January 2024
--   4. Surrogate key: MD5 hash of composite natural key
--   5. Partition column: pickup_date (for Iceberg partitioning)
-- =============================================================================

-- Use the Iceberg catalog
USE CATALOG iceberg_catalog;

-- Create the Silver database
CREATE DATABASE IF NOT EXISTS silver;
USE silver;

-- Create the Silver cleaned trips table
CREATE TABLE IF NOT EXISTS cleaned_trips (
    -- surrogate key
    trip_id                 STRING,

    -- identifiers
    vendor_id               INT,
    rate_code_id            INT,
    pickup_location_id      INT,
    dropoff_location_id     INT,
    payment_type_id         INT,

    -- timestamps
    pickup_datetime         TIMESTAMP(3),
    dropoff_datetime        TIMESTAMP(3),

    -- trip info
    passenger_count         INT,
    trip_distance_miles     DOUBLE,
    store_and_fwd_flag      STRING,

    -- financials
    fare_amount             DECIMAL(10, 2),
    extra_amount            DECIMAL(10, 2),
    mta_tax                 DECIMAL(10, 2),
    tip_amount              DECIMAL(10, 2),
    tolls_amount            DECIMAL(10, 2),
    improvement_surcharge   DECIMAL(10, 2),
    total_amount            DECIMAL(10, 2),
    congestion_surcharge    DECIMAL(10, 2),
    airport_fee             DECIMAL(10, 2),

    -- computed: time dimensions
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

-- Continuous INSERT from Bronze into Silver with transformations
INSERT INTO iceberg_catalog.silver.cleaned_trips
SELECT
    -- Surrogate key: MD5 hash of composite natural key
    MD5(CONCAT_WS('|',
        CAST(VendorID AS STRING),
        CAST(tpep_pickup_datetime AS STRING),
        CAST(tpep_dropoff_datetime AS STRING),
        CAST(PULocationID AS STRING),
        CAST(DOLocationID AS STRING),
        CAST(fare_amount AS STRING),
        CAST(total_amount AS STRING)
    )) AS trip_id,

    -- Identifiers (renamed + cast)
    CAST(VendorID AS INT)       AS vendor_id,
    CAST(RatecodeID AS INT)     AS rate_code_id,
    CAST(PULocationID AS INT)   AS pickup_location_id,
    CAST(DOLocationID AS INT)   AS dropoff_location_id,
    CAST(payment_type AS INT)   AS payment_type_id,

    -- Timestamps
    tpep_pickup_datetime        AS pickup_datetime,
    tpep_dropoff_datetime       AS dropoff_datetime,

    -- Trip info
    CAST(passenger_count AS INT) AS passenger_count,
    trip_distance               AS trip_distance_miles,
    store_and_fwd_flag,

    -- Financials (rounded to 2 decimal places)
    CAST(ROUND(fare_amount, 2)             AS DECIMAL(10, 2)) AS fare_amount,
    CAST(ROUND(extra, 2)                   AS DECIMAL(10, 2)) AS extra_amount,
    CAST(ROUND(mta_tax, 2)                 AS DECIMAL(10, 2)) AS mta_tax,
    CAST(ROUND(tip_amount, 2)              AS DECIMAL(10, 2)) AS tip_amount,
    CAST(ROUND(tolls_amount, 2)            AS DECIMAL(10, 2)) AS tolls_amount,
    CAST(ROUND(improvement_surcharge, 2)   AS DECIMAL(10, 2)) AS improvement_surcharge,
    CAST(ROUND(total_amount, 2)            AS DECIMAL(10, 2)) AS total_amount,
    CAST(ROUND(congestion_surcharge, 2)    AS DECIMAL(10, 2)) AS congestion_surcharge,
    CAST(ROUND(Airport_fee, 2)             AS DECIMAL(10, 2)) AS airport_fee,

    -- Computed: date dimensions
    CAST(tpep_pickup_datetime AS DATE) AS pickup_date

FROM iceberg_catalog.bronze.raw_trips

-- Data quality filters
WHERE tpep_pickup_datetime IS NOT NULL
  AND tpep_dropoff_datetime IS NOT NULL
  AND trip_distance >= 0
  AND fare_amount >= 0
  AND CAST(tpep_pickup_datetime AS DATE) >= DATE '2024-01-01'
  AND CAST(tpep_pickup_datetime AS DATE) <  DATE '2024-02-01';

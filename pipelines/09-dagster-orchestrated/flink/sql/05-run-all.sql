-- =============================================================================
-- Pipeline 01: Flink SQL - Full Pipeline (Bronze + Silver)
-- =============================================================================
-- Run with init: sql-client.sh embedded -i 00-init.sql -f 05-run-all.sql
-- =============================================================================

-- ═══════════════════════════════════════════════════════════════════════════════
-- BRONZE LAYER: Raw data from Kafka → Iceberg
-- ═══════════════════════════════════════════════════════════════════════════════

USE CATALOG iceberg_catalog;
CREATE DATABASE IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS bronze.raw_trips (
    VendorID                BIGINT,
    tpep_pickup_datetime    TIMESTAMP(3),
    tpep_dropoff_datetime   TIMESTAMP(3),
    passenger_count         BIGINT,
    trip_distance           DOUBLE,
    RatecodeID              BIGINT,
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
    Airport_fee             DOUBLE,
    ingestion_ts            TIMESTAMP(3)
);

-- Switch back to default catalog for Kafka source table reference
USE CATALOG default_catalog;
USE default_database;

-- Insert from Kafka into Bronze Iceberg table
INSERT INTO iceberg_catalog.bronze.raw_trips
SELECT
    VendorID,
    TO_TIMESTAMP(tpep_pickup_datetime, 'yyyy-MM-dd''T''HH:mm:ss')   AS tpep_pickup_datetime,
    TO_TIMESTAMP(tpep_dropoff_datetime, 'yyyy-MM-dd''T''HH:mm:ss')  AS tpep_dropoff_datetime,
    passenger_count,
    trip_distance,
    RatecodeID,
    store_and_fwd_flag,
    PULocationID,
    DOLocationID,
    payment_type,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    congestion_surcharge,
    Airport_fee,
    CURRENT_TIMESTAMP AS ingestion_ts
FROM kafka_raw_trips;

-- ═══════════════════════════════════════════════════════════════════════════════
-- SILVER LAYER: Cleaned + enriched data from Bronze → Silver
-- ═══════════════════════════════════════════════════════════════════════════════

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
    duration_minutes        BIGINT,
    avg_speed_mph           DOUBLE,
    cost_per_mile           DOUBLE,
    tip_percentage          DOUBLE,
    pickup_date             DATE,
    pickup_hour             INT,
    is_weekend              BOOLEAN
);

INSERT INTO iceberg_catalog.silver.cleaned_trips
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
    CAST(TIMESTAMPDIFF(MINUTE, tpep_pickup_datetime, tpep_dropoff_datetime) AS BIGINT) AS duration_minutes,
    CASE
        WHEN TIMESTAMPDIFF(MINUTE, tpep_pickup_datetime, tpep_dropoff_datetime) > 0
        THEN ROUND(
            trip_distance / (CAST(TIMESTAMPDIFF(MINUTE, tpep_pickup_datetime, tpep_dropoff_datetime) AS DOUBLE) / 60.0),
            2
        )
        ELSE NULL
    END AS avg_speed_mph,
    CASE
        WHEN trip_distance > 0
        THEN ROUND(fare_amount / trip_distance, 2)
        ELSE NULL
    END AS cost_per_mile,
    CASE
        WHEN fare_amount > 0
        THEN ROUND((tip_amount / fare_amount) * 100, 2)
        ELSE NULL
    END AS tip_percentage,
    CAST(tpep_pickup_datetime AS DATE) AS pickup_date,
    CAST(EXTRACT(HOUR FROM tpep_pickup_datetime) AS INT) AS pickup_hour,
    CASE
        WHEN DAYOFWEEK(tpep_pickup_datetime) IN (1, 7) THEN TRUE
        ELSE FALSE
    END AS is_weekend
FROM iceberg_catalog.bronze.raw_trips
WHERE tpep_pickup_datetime IS NOT NULL
  AND tpep_dropoff_datetime IS NOT NULL
  AND trip_distance >= 0
  AND fare_amount >= 0
  AND CAST(tpep_pickup_datetime AS DATE) >= DATE '2024-01-01'
  AND CAST(tpep_pickup_datetime AS DATE) <  DATE '2024-02-01';

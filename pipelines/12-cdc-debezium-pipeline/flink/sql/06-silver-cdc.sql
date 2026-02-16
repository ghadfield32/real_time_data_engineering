-- =============================================================================
-- Pipeline 12: Silver Layer (Bronze CDC -> Cleaned Iceberg)
-- =============================================================================
-- Run: sql-client.sh embedded -i 00-init.sql -f 06-silver-cdc.sql
-- =============================================================================
-- Parses CDC JSON payloads from Bronze, extracts the after-image (current
-- state of each row), applies quality filters, and writes to Silver.
--
-- Debezium CDC JSON structure (with schemas disabled):
-- {
--   "before": null | { ... },
--   "after": { "VendorID": 2, "tpep_pickup_datetime": 1706745600000000, ... },
--   "source": { ... },
--   "op": "c" | "u" | "d" | "r",
--   "ts_ms": 1706745600000
-- }
--
-- Note: Debezium outputs timestamps as microseconds since epoch when using
-- time.precision.mode=connect. We divide by 1,000,000 to get seconds.
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
    duration_minutes        BIGINT,
    avg_speed_mph           DOUBLE,
    cost_per_mile           DOUBLE,
    tip_percentage          DOUBLE,
    pickup_date             DATE,
    pickup_hour             INT,
    is_weekend              BOOLEAN
);

-- Parse CDC JSON and extract after-image fields, apply quality filters
-- Only process records where op is 'c' (create), 'r' (read/snapshot), or 'u' (update)
-- Skip 'd' (delete) operations since we want the current state
INSERT INTO iceberg_catalog.silver.cleaned_trips
SELECT
    CAST(MD5(CONCAT_WS('|',
        CAST(CAST(JSON_VALUE(cdc_payload, '$.after.VendorID') AS INT) AS STRING),
        CAST(CAST(JSON_VALUE(cdc_payload, '$.after.tpep_pickup_datetime') AS BIGINT) AS STRING),
        CAST(CAST(JSON_VALUE(cdc_payload, '$.after.tpep_dropoff_datetime') AS BIGINT) AS STRING),
        CAST(CAST(JSON_VALUE(cdc_payload, '$.after.PULocationID') AS INT) AS STRING),
        CAST(CAST(JSON_VALUE(cdc_payload, '$.after.DOLocationID') AS INT) AS STRING),
        JSON_VALUE(cdc_payload, '$.after.fare_amount'),
        JSON_VALUE(cdc_payload, '$.after.total_amount')
    )) AS STRING) AS trip_id,

    CAST(JSON_VALUE(cdc_payload, '$.after.VendorID') AS INT) AS vendor_id,
    CAST(JSON_VALUE(cdc_payload, '$.after.RatecodeID') AS INT) AS rate_code_id,
    CAST(JSON_VALUE(cdc_payload, '$.after.PULocationID') AS INT) AS pickup_location_id,
    CAST(JSON_VALUE(cdc_payload, '$.after.DOLocationID') AS INT) AS dropoff_location_id,
    CAST(JSON_VALUE(cdc_payload, '$.after.payment_type') AS INT) AS payment_type_id,

    TO_TIMESTAMP_LTZ(
        CAST(JSON_VALUE(cdc_payload, '$.after.tpep_pickup_datetime') AS BIGINT) / 1000000,
        0
    ) AS pickup_datetime,
    TO_TIMESTAMP_LTZ(
        CAST(JSON_VALUE(cdc_payload, '$.after.tpep_dropoff_datetime') AS BIGINT) / 1000000,
        0
    ) AS dropoff_datetime,

    CAST(JSON_VALUE(cdc_payload, '$.after.passenger_count') AS INT) AS passenger_count,
    CAST(JSON_VALUE(cdc_payload, '$.after.trip_distance') AS DOUBLE) AS trip_distance_miles,
    JSON_VALUE(cdc_payload, '$.after.store_and_fwd_flag') AS store_and_fwd_flag,

    CAST(ROUND(CAST(JSON_VALUE(cdc_payload, '$.after.fare_amount') AS DOUBLE), 2) AS DECIMAL(10, 2)) AS fare_amount,
    CAST(ROUND(CAST(JSON_VALUE(cdc_payload, '$.after.extra') AS DOUBLE), 2) AS DECIMAL(10, 2)) AS extra_amount,
    CAST(ROUND(CAST(JSON_VALUE(cdc_payload, '$.after.mta_tax') AS DOUBLE), 2) AS DECIMAL(10, 2)) AS mta_tax,
    CAST(ROUND(CAST(JSON_VALUE(cdc_payload, '$.after.tip_amount') AS DOUBLE), 2) AS DECIMAL(10, 2)) AS tip_amount,
    CAST(ROUND(CAST(JSON_VALUE(cdc_payload, '$.after.tolls_amount') AS DOUBLE), 2) AS DECIMAL(10, 2)) AS tolls_amount,
    CAST(ROUND(CAST(JSON_VALUE(cdc_payload, '$.after.improvement_surcharge') AS DOUBLE), 2) AS DECIMAL(10, 2)) AS improvement_surcharge,
    CAST(ROUND(CAST(JSON_VALUE(cdc_payload, '$.after.total_amount') AS DOUBLE), 2) AS DECIMAL(10, 2)) AS total_amount,
    CAST(ROUND(CAST(JSON_VALUE(cdc_payload, '$.after.congestion_surcharge') AS DOUBLE), 2) AS DECIMAL(10, 2)) AS congestion_surcharge,
    CAST(ROUND(CAST(JSON_VALUE(cdc_payload, '$.after.Airport_fee') AS DOUBLE), 2) AS DECIMAL(10, 2)) AS airport_fee,

    -- Derived: duration in minutes
    CAST(
        (CAST(JSON_VALUE(cdc_payload, '$.after.tpep_dropoff_datetime') AS BIGINT)
         - CAST(JSON_VALUE(cdc_payload, '$.after.tpep_pickup_datetime') AS BIGINT))
        / 60000000
    AS BIGINT) AS duration_minutes,

    -- Derived: average speed in mph
    CASE
        WHEN (CAST(JSON_VALUE(cdc_payload, '$.after.tpep_dropoff_datetime') AS BIGINT)
              - CAST(JSON_VALUE(cdc_payload, '$.after.tpep_pickup_datetime') AS BIGINT)) > 0
        THEN ROUND(
            CAST(JSON_VALUE(cdc_payload, '$.after.trip_distance') AS DOUBLE) /
            (CAST(
                (CAST(JSON_VALUE(cdc_payload, '$.after.tpep_dropoff_datetime') AS BIGINT)
                 - CAST(JSON_VALUE(cdc_payload, '$.after.tpep_pickup_datetime') AS BIGINT))
            AS DOUBLE) / 3600000000.0),
            2
        )
        ELSE NULL
    END AS avg_speed_mph,

    -- Derived: cost per mile
    CASE
        WHEN CAST(JSON_VALUE(cdc_payload, '$.after.trip_distance') AS DOUBLE) > 0
        THEN ROUND(
            CAST(JSON_VALUE(cdc_payload, '$.after.fare_amount') AS DOUBLE) /
            CAST(JSON_VALUE(cdc_payload, '$.after.trip_distance') AS DOUBLE),
            2
        )
        ELSE NULL
    END AS cost_per_mile,

    -- Derived: tip percentage
    CASE
        WHEN CAST(JSON_VALUE(cdc_payload, '$.after.fare_amount') AS DOUBLE) > 0
        THEN ROUND(
            (CAST(JSON_VALUE(cdc_payload, '$.after.tip_amount') AS DOUBLE) /
             CAST(JSON_VALUE(cdc_payload, '$.after.fare_amount') AS DOUBLE)) * 100,
            2
        )
        ELSE NULL
    END AS tip_percentage,

    -- Derived: pickup date
    CAST(
        TO_TIMESTAMP_LTZ(
            CAST(JSON_VALUE(cdc_payload, '$.after.tpep_pickup_datetime') AS BIGINT) / 1000000,
            0
        ) AS DATE
    ) AS pickup_date,

    -- Derived: pickup hour
    CAST(EXTRACT(HOUR FROM
        TO_TIMESTAMP_LTZ(
            CAST(JSON_VALUE(cdc_payload, '$.after.tpep_pickup_datetime') AS BIGINT) / 1000000,
            0
        )
    ) AS INT) AS pickup_hour,

    -- Derived: is weekend
    CASE
        WHEN DAYOFWEEK(
            TO_TIMESTAMP_LTZ(
                CAST(JSON_VALUE(cdc_payload, '$.after.tpep_pickup_datetime') AS BIGINT) / 1000000,
                0
            )
        ) IN (1, 7) THEN TRUE
        ELSE FALSE
    END AS is_weekend

FROM iceberg_catalog.bronze.cdc_raw_trips
WHERE JSON_VALUE(cdc_payload, '$.after.VendorID') IS NOT NULL
  AND JSON_VALUE(cdc_payload, '$.op') IN ('c', 'r', 'u')
  AND CAST(JSON_VALUE(cdc_payload, '$.after.trip_distance') AS DOUBLE) >= 0
  AND CAST(JSON_VALUE(cdc_payload, '$.after.fare_amount') AS DOUBLE) >= 0;

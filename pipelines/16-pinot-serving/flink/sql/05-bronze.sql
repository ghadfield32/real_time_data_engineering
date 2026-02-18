-- =============================================================================
-- Pipeline 16: Bronze Layer (Kafka -> Iceberg)
-- =============================================================================
-- Run: sql-client.sh embedded -i 00-init.sql -f 05-bronze.sql
-- =============================================================================

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
)
WITH (
    'format-version' = '1',
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'zstd',
    'write.metadata.delete-after-commit.enabled' = 'true',
    'write.metadata.previous-versions-max' = '10',
    'write.target-file-size-bytes' = '134217728'
);

USE CATALOG default_catalog;
USE default_database;

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

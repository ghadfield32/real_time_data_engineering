-- =============================================================================
-- Pipeline 01: Flink SQL - Bronze Layer (Raw Trips)
-- =============================================================================
-- Creates the Bronze Iceberg table and starts a continuous INSERT job
-- that reads from the Kafka source table.
--
-- Bronze layer preserves original column names from the source data.
-- Timestamps are parsed from ISO 8601 strings to TIMESTAMP type.
-- No filtering or cleaning is applied at this layer.
-- =============================================================================

-- Use the Iceberg catalog
USE CATALOG iceberg_catalog;

-- Create the Bronze database
CREATE DATABASE IF NOT EXISTS bronze;
USE bronze;

-- Create the Bronze raw trips table
CREATE TABLE IF NOT EXISTS raw_trips (
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

-- Switch back to default catalog for the Kafka source table reference
USE CATALOG default_catalog;
USE default_database;

-- Continuous INSERT from Kafka into Bronze Iceberg table
-- Timestamps are parsed from ISO 8601 string format (e.g. "2024-01-15T08:30:00")
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

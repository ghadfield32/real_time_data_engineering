-- =============================================================================
-- Pipeline 01: Streaming Bronze Layer (Kafka → Iceberg, continuous)
-- =============================================================================
-- Alternative to 05-bronze.sql that runs in STREAMING mode.
-- Uses event_time watermarks defined in 00-init.sql for event-time processing.
--
-- Run: sql-client.sh embedded -i 00-init-streaming.sql -f 07-streaming-bronze.sql
--   (or override execution.runtime-mode inline)
--
-- NOTE: This job runs continuously until cancelled. It will process new Kafka
-- events as they arrive and write them to the Bronze Iceberg table.
-- =============================================================================

-- Override to streaming mode (00-init.sql sets batch by default)
SET 'execution.runtime-mode' = 'streaming';

-- Don't wait for each INSERT to complete (streaming jobs run indefinitely)
RESET 'table.dml-sync';

-- Checkpoint every 30s for exactly-once guarantees
SET 'execution.checkpointing.interval' = '30s';

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

-- Streaming INSERT: runs continuously, processing new Kafka events as they arrive
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

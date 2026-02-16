-- =============================================================================
-- Pipeline 01: Flink SQL - Session Initialization (REST Catalog via Lakekeeper)
-- =============================================================================
-- Alternative to 00-init.sql that uses Lakekeeper REST catalog instead of
-- Hadoop catalog. Requires: docker compose --profile lakekeeper up -d
--
-- Usage:
--   sql-client.sh embedded -i 00-init-rest.sql -f 05-bronze.sql
--   sql-client.sh embedded -i 00-init-rest.sql -f 06-silver.sql
-- =============================================================================

-- Use batch mode (process available data, then stop)
SET 'execution.runtime-mode' = 'batch';

-- Wait for each INSERT to complete before proceeding to next statement
SET 'table.dml-sync' = 'true';

-- Create Kafka source table
-- NOTE: event_time computed column + WATERMARK enables event-time processing
-- in streaming mode. In batch mode (default), the watermark is simply ignored.
CREATE TABLE IF NOT EXISTS kafka_raw_trips (
    VendorID                BIGINT,
    tpep_pickup_datetime    STRING,
    tpep_dropoff_datetime   STRING,
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
    -- Computed column for event-time processing
    event_time AS TO_TIMESTAMP(tpep_pickup_datetime, 'yyyy-MM-dd''T''HH:mm:ss'),
    -- Watermark: allow 10s late arrivals (ignored in batch mode)
    WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'taxi.raw_trips',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-consumer',
    'scan.startup.mode' = 'earliest-offset',
    'scan.bounded.mode' = 'latest-offset',
    'format' = 'json'
);

-- Create Iceberg catalog via Lakekeeper REST API
-- No S3 credentials needed here - Lakekeeper handles credential vending
CREATE CATALOG iceberg_catalog WITH (
    'type' = 'iceberg',
    'catalog-type' = 'rest',
    'uri' = 'http://lakekeeper:8181/catalog',
    'warehouse' = 'warehouse'
);

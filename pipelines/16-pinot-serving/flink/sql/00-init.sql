-- =============================================================================
-- Pipeline 16: Flink SQL - Session Initialization
-- =============================================================================
-- Creates the Kafka source table and Iceberg catalog. This file is used as
-- an init script (-i flag) for all subsequent SQL files so they have access
-- to the catalog within the same session.
--
-- Uses BATCH execution mode so jobs process all available data and terminate.
-- =============================================================================

-- Use batch mode (process available data, then stop)
SET 'execution.runtime-mode' = 'batch';

-- Wait for each INSERT to complete before proceeding to next statement
SET 'table.dml-sync' = 'true';

-- Create Kafka source table
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
    Airport_fee             DOUBLE
) WITH (
    'connector' = 'kafka',
    'topic' = 'taxi.raw_trips',
    'properties.bootstrap.servers' = 'redpanda:9092',
    'properties.group.id' = 'flink-consumer',
    'scan.startup.mode' = 'earliest-offset',
    'scan.bounded.mode' = 'latest-offset',
    'format' = 'json'
);

-- Create Iceberg catalog backed by MinIO
CREATE CATALOG iceberg_catalog WITH (
    'type' = 'iceberg',
    'catalog-type' = 'hadoop',
    'warehouse' = 's3a://warehouse/',
    'io-impl' = 'org.apache.iceberg.aws.s3.S3FileIO',
    's3.endpoint' = 'http://minio:9000',
    's3.access-key-id' = 'minioadmin',
    's3.secret-access-key' = 'minioadmin',
    's3.path-style-access' = 'true'
);

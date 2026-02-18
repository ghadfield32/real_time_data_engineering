-- =============================================================================
-- Pipeline 01: Flink SQL - Streaming Session Initialization
-- =============================================================================
-- Creates the Kafka source table and Iceberg catalog for STREAMING mode.
-- Unlike 00-init.sql (batch), this file:
--   - Sets execution.runtime-mode = streaming
--   - Enables checkpointing for exactly-once guarantees
--   - Does NOT set scan.bounded.mode (so the Kafka source never terminates)
--   - Uses scan.startup.mode = latest-offset (process new events only)
--
-- Usage: sql-client.sh embedded -i 00-init-streaming.sql -f 07-streaming-bronze.sql
-- =============================================================================

-- Use streaming mode (job runs indefinitely)
SET 'execution.runtime-mode' = 'streaming';

-- Checkpoint every 30s for exactly-once guarantees
SET 'execution.checkpointing.interval' = '30s';

-- Create Kafka source table (streaming — no bounded mode)
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
    -- Watermark: allow 10s late arrivals
    WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'taxi.raw_trips',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-streaming-consumer',
    'scan.startup.mode' = 'latest-offset',
    -- NOTE: No scan.bounded.mode — this is what makes it truly streaming.
    -- The job will run indefinitely, processing new Kafka events as they arrive.
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

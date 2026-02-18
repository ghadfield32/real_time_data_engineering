-- =============================================================================
-- Template Pipeline: Flink SQL - Streaming Session Initialization
-- =============================================================================
-- PURPOSE: Creates the Redpanda source table and Iceberg catalog for
--          CONTINUOUS STREAMING mode. Unlike 00-init.sql (batch), this:
--            - Sets execution.runtime-mode = streaming
--            - Enables checkpointing for exactly-once guarantees
--            - Omits scan.bounded.mode (source never terminates)
--            - Uses scan.startup.mode = latest-offset (new events only)
--
-- USAGE:
--   sql-client.sh embedded -i 00-init-streaming.sql -f 07-streaming-bronze.sql
--
-- The job runs indefinitely. Cancel via:
--   Flink Dashboard → Jobs → Cancel   OR   Ctrl+C in the terminal
--
-- ============================================================
-- CUSTOMIZATION: Replace all TODO markers before using.
-- Same column changes as 00-init.sql apply here.
-- ============================================================

-- Streaming mode: job runs indefinitely
SET 'execution.runtime-mode' = 'streaming';

-- Checkpoint every 30s for exactly-once delivery to Iceberg
SET 'execution.checkpointing.interval' = '30s';

-- CRITICAL: Do NOT set table.dml-sync in streaming mode.
-- dml-sync=true would hang the session waiting for the infinite job to finish.

-- =============================================================================
-- SOURCE TABLE: Redpanda / Kafka (streaming — no bounded mode)
-- =============================================================================
-- TODO: Mirror the column changes you made in 00-init.sql exactly.
--       The two files must have identical column lists.
CREATE TABLE IF NOT EXISTS kafka_raw_events (
    -- TODO: Add your columns here (same as 00-init.sql)
    -- COLUMN_1  TYPE_1,
    -- COLUMN_2  TYPE_2,

    event_time AS TO_TIMESTAMP(YOUR_TIMESTAMP_FIELD, 'yyyy-MM-dd''T''HH:mm:ss'),
    WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
) WITH (
    'connector'                       = 'kafka',
    'topic'                           = 'DOMAIN.raw_events',    -- TODO: replace DOMAIN
    'properties.bootstrap.servers'    = 'redpanda:9092',
    'properties.group.id'             = 'flink-streaming-consumer',
    'scan.startup.mode'               = 'latest-offset',
    -- NOTE: No scan.bounded.mode — this makes the source truly unbounded.
    'format'                          = 'json'
);

-- =============================================================================
-- ICEBERG CATALOG (same as 00-init.sql — no changes needed)
-- =============================================================================
CREATE CATALOG iceberg_catalog WITH (
    'type'               = 'iceberg',
    'catalog-type'       = 'hadoop',
    'warehouse'          = 's3a://warehouse/',
    'io-impl'            = 'org.apache.iceberg.aws.s3.S3FileIO',
    's3.endpoint'        = 'http://minio:9000',
    's3.access-key-id'   = 'minioadmin',
    's3.secret-access-key' = 'minioadmin',
    's3.path-style-access' = 'true'
);

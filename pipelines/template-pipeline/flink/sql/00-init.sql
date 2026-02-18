-- =============================================================================
-- Template Pipeline: Flink SQL - Batch Session Initialization
-- =============================================================================
-- PURPOSE: Creates the Redpanda source table and Iceberg catalog.
-- USAGE:   Used as an init script (-i flag). All subsequent SQL files
--          (-f flag) share this session and can reference these objects.
--
-- BATCH MODE: processes all available messages in the topic then terminates.
-- Use this for scheduled batch loads (nightly, hourly replay, backfill).
--
-- Run:
--   sql-client.sh embedded -i 00-init.sql -f 05-bronze.sql
--   sql-client.sh embedded -i 00-init.sql -f 06-silver.sql
--
-- ============================================================
-- CUSTOMIZATION: Replace all TODO markers before using.
-- ============================================================

-- Use batch mode (drain topic to latest-offset, then stop)
SET 'execution.runtime-mode' = 'batch';

-- Wait for each INSERT to complete before proceeding to the next statement.
-- CRITICAL: without this, 05-bronze.sql and 06-silver.sql would run in parallel,
-- causing the silver INSERT to fail because bronze doesn't exist yet.
SET 'table.dml-sync' = 'true';

-- =============================================================================
-- SOURCE TABLE: Redpanda / Kafka (JSON format)
-- =============================================================================
-- DECISION: All columns ingested as STRING or numeric primitives.
-- Avoid parsing timestamps here — do it in 05-bronze.sql with TO_TIMESTAMP().
-- This makes the schema forgiving: a bad timestamp won't kill the job.
--
-- TODO: Replace column names and types to match YOUR dataset's JSON schema.
--       Run `rpk topic consume DOMAIN.raw_events --num 1` to see a sample message.
--
-- COLUMN TYPE GUIDE:
--   STRING  → any text field, IDs, flags, raw timestamps
--   BIGINT  → integer IDs, counts (use BIGINT not INT for Kafka JSON safety)
--   DOUBLE  → decimal measurements, amounts
--   BOOLEAN → true/false fields
-- =============================================================================
CREATE TABLE IF NOT EXISTS kafka_raw_events (
    -- TODO: Add your columns here. Example for NYC Taxi:
    -- VendorID             BIGINT,
    -- tpep_pickup_datetime STRING,   -- raw timestamp string; parse in bronze
    -- trip_distance        DOUBLE,
    -- fare_amount          DOUBLE,

    -- COLUMN_1  TYPE_1,   -- TODO: replace
    -- COLUMN_2  TYPE_2,   -- TODO: replace
    -- ...

    -- Computed event-time column (derived from your primary timestamp field).
    -- In BATCH mode, the watermark is ignored — include it anyway for streaming parity.
    -- TODO: Replace YOUR_TIMESTAMP_FIELD and adjust the format pattern to match your data.
    --   Common patterns:
    --     'yyyy-MM-dd''T''HH:mm:ss'   → ISO 8601 without timezone  (e.g. 2024-01-15T09:32:11)
    --     'yyyy-MM-dd HH:mm:ss'       → SQL-style datetime
    --     'yyyy-MM-dd''T''HH:mm:ssXXX'→ ISO 8601 with timezone offset
    event_time AS TO_TIMESTAMP(YOUR_TIMESTAMP_FIELD, 'yyyy-MM-dd''T''HH:mm:ss'),
    WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
) WITH (
    'connector'                       = 'kafka',
    'topic'                           = 'DOMAIN.raw_events',    -- TODO: replace DOMAIN
    'properties.bootstrap.servers'    = 'redpanda:9092',
    'properties.group.id'             = 'flink-consumer',
    'scan.startup.mode'               = 'earliest-offset',
    'scan.bounded.mode'               = 'latest-offset',        -- batch: stop at current end
    'format'                          = 'json'
);

-- =============================================================================
-- ICEBERG CATALOG (Hadoop catalog backed by MinIO)
-- =============================================================================
-- No changes needed here unless you switch to a REST catalog (e.g. Lakekeeper).
-- The Hadoop catalog stores metadata as files directly in MinIO.
-- Namespace layout: s3a://warehouse/<database>/<table>/
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

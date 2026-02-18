-- =============================================================================
-- Template Pipeline: Streaming Bronze Layer (Redpanda → Iceberg, continuous)
-- =============================================================================
-- PURPOSE: Alternative to 05-bronze.sql that runs in STREAMING mode.
--          Processes new Redpanda events continuously as they arrive.
--
-- Run: sql-client.sh embedded -i 00-init-streaming.sql -f 07-streaming-bronze.sql
--
-- DIFFERENCE FROM 05-bronze.sql:
--   - 05-bronze.sql: batch mode, drains topic to latest-offset, terminates
--   - 07-streaming-bronze.sql: streaming mode, runs forever, new events only
--
-- WHEN TO USE WHICH:
--   Batch (05): scheduled backfills, historical loads, overnight processing
--   Streaming (07): real-time ingestion when events must appear < 30s after arrival
--
-- ============================================================
-- CUSTOMIZATION: Mirror the column changes from 05-bronze.sql exactly.
-- ============================================================

USE CATALOG iceberg_catalog;
CREATE DATABASE IF NOT EXISTS bronze;

-- =============================================================================
-- BRONZE TABLE (same DDL as 05-bronze.sql — must be identical)
-- =============================================================================
-- TODO: Copy your finalized CREATE TABLE from 05-bronze.sql here exactly.
CREATE TABLE IF NOT EXISTS bronze.raw_events (
    -- TODO: Mirror columns from 05-bronze.sql
    -- COLUMN_1  TYPE_1,
    -- COLUMN_2  TYPE_2,
    ingestion_ts  TIMESTAMP(3)
)
WITH (
    'format-version'                            = '1',
    'write.format.default'                      = 'parquet',
    'write.parquet.compression-codec'           = 'zstd',
    'write.metadata.delete-after-commit.enabled' = 'true',
    'write.metadata.previous-versions-max'      = '10',
    'write.target-file-size-bytes'              = '134217728'
);

-- Switch back to default catalog to reference the streaming Kafka source
USE CATALOG default_catalog;
USE default_database;

-- =============================================================================
-- STREAMING INSERT: Redpanda → Bronze Iceberg (runs indefinitely)
-- =============================================================================
-- Checkpoints every 30s (set in 00-init-streaming.sql) commit Iceberg snapshots.
-- Each checkpoint = one Iceberg snapshot = one set of visible Parquet files.
-- Files become visible to dbt queries only after a checkpoint commits.
--
-- TODO: Mirror the SELECT columns from 05-bronze.sql exactly.
INSERT INTO iceberg_catalog.bronze.raw_events
SELECT
    -- TODO: Mirror column mappings from 05-bronze.sql
    -- COLUMN_1,
    -- TO_TIMESTAMP(TIMESTAMP_FIELD, 'yyyy-MM-dd''T''HH:mm:ss') AS parsed_timestamp,
    CURRENT_TIMESTAMP AS ingestion_ts
FROM kafka_raw_events;

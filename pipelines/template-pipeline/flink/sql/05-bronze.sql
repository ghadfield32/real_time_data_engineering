-- =============================================================================
-- Template Pipeline: Bronze Layer (Redpanda → Iceberg)
-- =============================================================================
-- PURPOSE: Creates the Bronze Iceberg table and inserts all raw events.
--
-- Bronze Layer Contract:
--   ✓ Raw data — preserve original values, do NOT rename or recast columns
--   ✓ Add ingestion_ts metadata column (CURRENT_TIMESTAMP at Flink job time)
--   ✓ Parse timestamp strings into TIMESTAMP(3) using TO_TIMESTAMP()
--   ✓ Leave data quality issues intact — Bronze is the source of truth
--   ✗ Do NOT deduplicate (that's Silver's job)
--   ✗ Do NOT rename columns to snake_case (that's Silver's job)
--   ✗ Do NOT filter rows (Silver filters; Bronze archives everything)
--   ✗ Do NOT partition Bronze (it's append-only raw landing)
--
-- Run: sql-client.sh embedded -i 00-init.sql -f 05-bronze.sql
--
-- ============================================================
-- CUSTOMIZATION: Replace column definitions to match your dataset.
-- ============================================================

USE CATALOG iceberg_catalog;
CREATE DATABASE IF NOT EXISTS bronze;

-- =============================================================================
-- BRONZE TABLE DEFINITION
-- =============================================================================
-- Column types here are the "parsed" types — slightly cleaner than Kafka source.
-- Example conversions:
--   STRING timestamp → TIMESTAMP(3) via TO_TIMESTAMP() in the INSERT below
--   BIGINT IDs stay BIGINT (INT is too narrow for JSON safety)
--   DOUBLE amounts stay DOUBLE (DECIMAL rounding happens in Silver)
--
-- TODO: Replace COLUMN_* with your dataset's actual column names and types.
-- TODO: Preserve the raw Kafka field names (e.g., VendorID not vendor_id).
-- =============================================================================
CREATE TABLE IF NOT EXISTS bronze.raw_events (
    -- TODO: Add your columns here. Example for NYC Taxi:
    -- VendorID                BIGINT,
    -- tpep_pickup_datetime    TIMESTAMP(3),   -- parsed from STRING in INSERT
    -- tpep_dropoff_datetime   TIMESTAMP(3),
    -- passenger_count         BIGINT,
    -- trip_distance           DOUBLE,
    -- fare_amount             DOUBLE,
    -- total_amount            DOUBLE,

    -- COLUMN_1                TYPE_1,        -- TODO: replace
    -- COLUMN_2                TYPE_2,        -- TODO: replace
    -- ...

    -- Metadata: when this row was ingested (not the event time)
    ingestion_ts            TIMESTAMP(3)
)
WITH (
    -- Bronze uses Iceberg v1 (append-only, no row-level deletes needed)
    'format-version'                            = '1',
    'write.format.default'                      = 'parquet',
    'write.parquet.compression-codec'           = 'zstd',
    -- Auto-delete old metadata files (keeps MinIO clean)
    'write.metadata.delete-after-commit.enabled' = 'true',
    'write.metadata.previous-versions-max'      = '10',
    -- Target 128MB Parquet files (fewer, larger files = faster scan)
    'write.target-file-size-bytes'              = '134217728'
);

-- Switch back to default catalog to reference the Kafka source table
USE CATALOG default_catalog;
USE default_database;

-- =============================================================================
-- INSERT: Redpanda → Bronze Iceberg
-- =============================================================================
-- Key transformations here:
--   1. Parse timestamp strings with TO_TIMESTAMP() using your format pattern
--   2. Add CURRENT_TIMESTAMP as ingestion_ts
--   3. Pass all other columns through as-is (no renaming, no filtering)
--
-- TODO: Match the SELECT columns exactly to your CREATE TABLE above.
-- TODO: Update the TO_TIMESTAMP format string to match your data's timestamp format.
-- =============================================================================
INSERT INTO iceberg_catalog.bronze.raw_events
SELECT
    -- TODO: Add your column mappings here. Example for NYC Taxi:
    -- VendorID,
    -- TO_TIMESTAMP(tpep_pickup_datetime, 'yyyy-MM-dd''T''HH:mm:ss') AS tpep_pickup_datetime,
    -- TO_TIMESTAMP(tpep_dropoff_datetime, 'yyyy-MM-dd''T''HH:mm:ss') AS tpep_dropoff_datetime,
    -- passenger_count,
    -- trip_distance,
    -- fare_amount,
    -- total_amount,

    -- COLUMN_1,             -- TODO: replace
    -- COLUMN_2,             -- TODO: replace

    CURRENT_TIMESTAMP AS ingestion_ts
FROM kafka_raw_events;

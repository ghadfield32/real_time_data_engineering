-- =============================================================================
-- Template Pipeline: Silver Layer (Bronze Iceberg → Silver Iceberg)
-- =============================================================================
-- PURPOSE: Reads Bronze, applies data quality, renames to snake_case,
--          deduplicates on natural key, and writes to partitioned Silver table.
--
-- Silver Layer Contract:
--   ✓ Snake_case column names (vendor_id not VendorID)
--   ✓ Correct types (INT not BIGINT for IDs; DECIMAL not DOUBLE for money)
--   ✓ Surrogate key (MD5 hash of natural key fields)
--   ✓ Deduplication via ROW_NUMBER() — latest ingestion wins
--   ✓ Data quality filters: reject nulls, negatives, out-of-range dates
--   ✓ Partition by date column (enables efficient time-range queries)
--   ✓ Iceberg format-version=2 (supports row-level deletes for MERGE INTO)
--   ✗ Do NOT add business logic or enrichment (that's dbt Gold's job)
--
-- Run: sql-client.sh embedded -i 00-init.sql -f 06-silver.sql
--
-- ============================================================
-- CUSTOMIZATION: The 5 areas marked TODO are where you customize.
-- ============================================================

USE CATALOG iceberg_catalog;
CREATE DATABASE IF NOT EXISTS silver;

-- =============================================================================
-- SILVER TABLE DEFINITION
-- =============================================================================
-- TODO (1/5): Update column list to match YOUR domain's cleaned schema.
-- Silver column naming rules:
--   - All snake_case (vendor_id, pickup_datetime, etc.)
--   - IDs as INT (not BIGINT — they fit, and INT is more memory-efficient)
--   - Monetary amounts as DECIMAL(10, 2)
--   - Raw strings stay STRING
--   - Timestamps stay TIMESTAMP(3)
--   - Add a DATE partition column as the last column (see pickup_date example)
-- =============================================================================
CREATE TABLE IF NOT EXISTS silver.cleaned_events (
    -- Surrogate key (always include — needed for MERGE INTO and dbt refs)
    event_id                STRING,

    -- TODO (1/5): Add your domain-specific columns below.
    -- Example for NYC Taxi:
    -- vendor_id               INT,
    -- rate_code_id            INT,
    -- pickup_location_id      INT,
    -- dropoff_location_id     INT,
    -- payment_type_id         INT,
    -- pickup_datetime         TIMESTAMP(3),
    -- dropoff_datetime        TIMESTAMP(3),
    -- passenger_count         INT,
    -- trip_distance_miles     DOUBLE,
    -- store_and_fwd_flag      STRING,
    -- fare_amount             DECIMAL(10, 2),
    -- total_amount            DECIMAL(10, 2),

    -- Partition column: must be a DATE derived from your primary timestamp.
    -- RULE: Always name this <domain>_date or event_date for clarity.
    -- RULE: Add it as the LAST column (Iceberg convention).
    event_date              DATE    -- TODO: rename to match your domain

) PARTITIONED BY (event_date)       -- TODO: update to match your partition column name
WITH (
    -- Silver uses Iceberg v2 (enables MERGE INTO for upserts if needed later)
    'format-version'                            = '2',
    'write.format.default'                      = 'parquet',
    'write.parquet.compression-codec'           = 'zstd',
    'write.metadata.delete-after-commit.enabled' = 'true',
    'write.metadata.previous-versions-max'      = '10',
    'write.target-file-size-bytes'              = '134217728'
);

-- =============================================================================
-- INSERT: Bronze → Silver (with deduplication via ROW_NUMBER)
-- =============================================================================
INSERT INTO iceberg_catalog.silver.cleaned_events
WITH deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            -- TODO (2/5): Define the NATURAL KEY for deduplication.
            -- Natural key = the combination of fields that uniquely identifies a real-world event.
            -- For NYC Taxi: VendorID + pickup_time + dropoff_time + locations + amounts
            -- For Stock Ticks: symbol + exchange + timestamp (+ sequence_no if available)
            -- For IoT: device_id + sensor_id + event_timestamp
            -- For Orders: order_id + line_item_id
            PARTITION BY NATURAL_KEY_COLUMN_1, NATURAL_KEY_COLUMN_2  -- TODO: replace
            ORDER BY ingestion_ts DESC   -- latest ingestion wins on duplicates
        ) AS rn
    FROM iceberg_catalog.bronze.raw_events

    -- TODO (3/5): Add data quality filters for YOUR dataset.
    -- RULES:
    --   - Reject NULL on any field required for the natural key (or the job fails on hash)
    --   - Reject NULL timestamps used for partitioning
    --   - Reject physically impossible values (negative distances, amounts)
    --   - Restrict date range to your dataset's valid window
    WHERE PRIMARY_TIMESTAMP_COLUMN IS NOT NULL   -- TODO: replace
      AND ANOTHER_REQUIRED_COLUMN IS NOT NULL    -- TODO: replace
      -- AND numeric_column >= 0                 -- reject negative values
      -- AND CAST(PRIMARY_TIMESTAMP_COLUMN AS DATE) >= DATE '2024-01-01'
      -- AND CAST(PRIMARY_TIMESTAMP_COLUMN AS DATE) <  DATE '2024-02-01'
)
SELECT
    -- Surrogate key: MD5 of the natural key fields (same fields as PARTITION BY above)
    -- TODO (4/5): Update CONCAT_WS fields to match YOUR natural key.
    CAST(MD5(CONCAT_WS('|',
        CAST(NATURAL_KEY_COLUMN_1 AS STRING),   -- TODO: replace
        CAST(NATURAL_KEY_COLUMN_2 AS STRING)    -- TODO: replace
        -- add more key fields as needed
    )) AS STRING) AS event_id,

    -- TODO (5/5): Map Bronze columns to Silver columns with renaming and type casts.
    -- PATTERNS:
    --   CAST(VendorID AS INT)                         AS vendor_id,
    --   CAST(ROUND(fare_amount, 2) AS DECIMAL(10, 2)) AS fare_amount,
    --   tpep_pickup_datetime                          AS pickup_datetime,
    --   CAST(tpep_pickup_datetime AS DATE)            AS pickup_date

    -- TODO: Add your column mappings here

    -- ALWAYS LAST: partition column derived from primary timestamp
    CAST(PRIMARY_TIMESTAMP_COLUMN AS DATE) AS event_date  -- TODO: rename column + update source

FROM deduped
WHERE rn = 1;

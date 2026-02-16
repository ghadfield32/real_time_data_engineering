-- =============================================================================
-- Pipeline 12: Flink SQL - Session Initialization
-- =============================================================================
-- Creates the Iceberg catalog for CDC pipeline. This file is used as an init
-- script (-i flag) for all subsequent SQL files so they share the same catalog
-- within a single session.
--
-- Uses BATCH execution mode so jobs process all available data and terminate.
-- =============================================================================

-- Use batch mode (process available data, then stop)
SET 'execution.runtime-mode' = 'batch';

-- Wait for each INSERT to complete before proceeding to next statement
SET 'table.dml-sync' = 'true';

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

CREATE DATABASE IF NOT EXISTS iceberg_catalog.bronze;
CREATE DATABASE IF NOT EXISTS iceberg_catalog.silver;

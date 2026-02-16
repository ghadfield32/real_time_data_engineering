-- =============================================================================
-- Pipeline 12: Bronze Layer (Kafka CDC Events -> Iceberg)
-- =============================================================================
-- Run: sql-client.sh embedded -i 00-init.sql -f 05-bronze-cdc.sql
-- =============================================================================
-- Reads raw Debezium CDC events from Kafka topic and stores them as-is in
-- Iceberg Bronze layer for auditability and reprocessing.
-- =============================================================================

-- Create Kafka source for Debezium CDC events (raw JSON)
CREATE TEMPORARY TABLE cdc_source (
    `payload` STRING
) WITH (
    'connector' = 'kafka',
    'topic' = 'dbserver1.public.taxi_trips',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-cdc-bronze',
    'scan.startup.mode' = 'earliest-offset',
    'scan.bounded.mode' = 'latest-offset',
    'format' = 'raw'
);

-- Create Iceberg Bronze table for raw CDC events
USE CATALOG iceberg_catalog;
CREATE DATABASE IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS bronze.cdc_raw_trips (
    cdc_payload       STRING,
    ingested_at       TIMESTAMP(3)
);

USE CATALOG default_catalog;
USE default_database;

-- Insert raw CDC events into Bronze
INSERT INTO iceberg_catalog.bronze.cdc_raw_trips
SELECT
    `payload` AS cdc_payload,
    CURRENT_TIMESTAMP AS ingested_at
FROM cdc_source;

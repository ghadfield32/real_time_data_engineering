-- =============================================================================
-- Benchmark Query 1: Daily Revenue Aggregation
-- =============================================================================
-- Purpose : Aggregate total trips, revenue, and average revenue per day.
-- Use case: Executive dashboard KPI, daily trend analysis.
-- Protocol: Run 10 iterations, discard first 2 warm-up runs, report p50/p95/p99.
--
-- Expected result columns:
--   day          DATE       -- calendar day
--   trips        BIGINT     -- total trip count
--   revenue      DECIMAL    -- SUM(total_amount)
--   avg_revenue  DECIMAL    -- AVG(total_amount)
-- =============================================================================


-- ---------------------------------------------------------------------------
-- Engine 1: DuckDB / Iceberg (via dbt fct_trips table)
-- ---------------------------------------------------------------------------
-- DuckDB supports standard DATE_TRUNC and runs against the Iceberg catalog
-- or direct Parquet/dbt-materialized tables.
--
-- SELECT
--     DATE_TRUNC('day', pickup_datetime)  AS day,
--     COUNT(*)                            AS trips,
--     SUM(total_amount)                   AS revenue,
--     ROUND(AVG(total_amount), 2)         AS avg_revenue
-- FROM fct_trips
-- GROUP BY 1
-- ORDER BY 1;


-- ---------------------------------------------------------------------------
-- Engine 2: ClickHouse
-- ---------------------------------------------------------------------------
-- ClickHouse uses toDate() for fast date truncation.  The table lives in the
-- nyc_taxi database, which mirrors the dbt mart schema.
--
-- SELECT
--     toDate(pickup_datetime)             AS day,
--     COUNT(*)                            AS trips,
--     SUM(total_amount)                   AS revenue,
--     ROUND(AVG(total_amount), 2)         AS avg_revenue
-- FROM nyc_taxi.fct_trips
-- GROUP BY day
-- ORDER BY day;


-- ---------------------------------------------------------------------------
-- Engine 3: RisingWave / Materialize  (PostgreSQL-compatible)
-- ---------------------------------------------------------------------------
-- Both engines speak Postgres wire protocol.  DATE_TRUNC returns a TIMESTAMP
-- so we cast to DATE for cleaner output.
--
-- SELECT
--     DATE_TRUNC('day', pickup_datetime)::DATE  AS day,
--     COUNT(*)                                  AS trips,
--     SUM(total_amount)                         AS revenue,
--     ROUND(AVG(total_amount), 2)               AS avg_revenue
-- FROM fct_trips
-- GROUP BY 1
-- ORDER BY 1;


-- ---------------------------------------------------------------------------
-- Engine 4: Apache Pinot
-- ---------------------------------------------------------------------------
-- Pinot ingests from Kafka with raw column names.  DATETIMECONVERT converts
-- the epoch-millis timestamp to a daily bucket string.
--
-- SELECT
--     DATETIMECONVERT(
--         tpep_pickup_datetime,
--         '1:MILLISECONDS:EPOCH',
--         '1:DAYS:SIMPLE_DATE_FORMAT:yyyy-MM-dd',
--         '1:DAYS'
--     )                                       AS day,
--     COUNT(*)                                AS trips,
--     SUM(total_amount)                       AS revenue,
--     ROUND(AVG(total_amount), 2)             AS avg_revenue
-- FROM taxi_trips
-- GROUP BY day
-- ORDER BY day
-- LIMIT 1000;


-- ---------------------------------------------------------------------------
-- Engine 5: Apache Druid
-- ---------------------------------------------------------------------------
-- Druid stores the ingestion timestamp as __time.  TIME_FLOOR buckets it to
-- day granularity using ISO 8601 period notation.
--
-- SELECT
--     TIME_FLOOR(__time, 'P1D')              AS day,
--     COUNT(*)                               AS trips,
--     SUM(total_amount)                      AS revenue,
--     ROUND(AVG(total_amount), 2)            AS avg_revenue
-- FROM taxi_trips
-- GROUP BY 1
-- ORDER BY 1;


-- ---------------------------------------------------------------------------
-- Engine 6: Spark SQL
-- ---------------------------------------------------------------------------
-- Spark SQL uses the nyc_taxi Hive/Iceberg catalog.  DATE_TRUNC or
-- to_date() both work; DATE_TRUNC keeps consistency with DuckDB.
--
-- SELECT
--     DATE_TRUNC('DAY', pickup_datetime)     AS day,
--     COUNT(*)                               AS trips,
--     SUM(total_amount)                      AS revenue,
--     ROUND(AVG(total_amount), 2)            AS avg_revenue
-- FROM nyc_taxi.fct_trips
-- GROUP BY 1
-- ORDER BY 1;

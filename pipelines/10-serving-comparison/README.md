# Pipeline 10: Serving Layer Comparison

This pipeline consumes **Gold-layer output** from any Tier 1 pipeline (01 through 09) and serves it through **ClickHouse** for high-performance OLAP queries. Two BI frontends -- **Metabase** and **Apache Superset** -- are provided side by side so you can compare their capabilities against the same data source.

## Architecture

```
+-------------------------------+
|  Tier 1 Pipeline Gold Output  |
|  (Parquet / CSV from dbt)     |
+---------------+---------------+
                |
                v
+---------------+---------------+
|         ClickHouse            |
|   (OLAP columnar engine)      |
|   - fct_trips                 |
|   - mart_daily_revenue        |
|   - mart_location_performance |
|   - mart_hourly_demand        |
|   - dim_locations             |
|   - dim_payment_types         |
+------+----------------+------+
       |                |
       v                v
+------+------+  +------+------+
|  Metabase   |  |  Superset   |
|  (BI Tool)  |  |  (BI Tool)  |
+-------------+  +-------------+
```

## Services

| Service    | Container        | Port(s)            | Description                        |
|------------|------------------|--------------------|------------------------------------|
| ClickHouse | p10-clickhouse   | 8123 (HTTP), 9100 (TCP) | Columnar OLAP database        |
| Metabase   | p10-metabase     | 3030               | Open-source BI / dashboarding     |
| Superset   | p10-superset     | 8088               | Apache BI platform (admin/admin)  |

## Quick Start

```bash
# Start all services
make up

# Check service status
make status

# Run benchmark queries (5 runs each, reports latency in ms)
make benchmark-queries

# Full benchmark (start services + run queries)
make benchmark

# View logs
make logs

# Tear down everything including volumes
make down
```

## Loading Gold-Layer Data

This pipeline does not generate its own data. It expects Gold-layer output from a Tier 1 pipeline. After running one of those pipelines, export the dbt mart tables to Parquet and load them into ClickHouse:

```bash
# Example: load fact trips from a Parquet file
docker exec -i p10-clickhouse clickhouse-client \
  --query "INSERT INTO nyc_taxi.fct_trips FORMAT Parquet" < fct_trips.parquet

# Example: load from CSV
docker exec -i p10-clickhouse clickhouse-client \
  --query "INSERT INTO nyc_taxi.mart_daily_revenue FORMAT CSVWithNames" < mart_daily_revenue.csv
```

Dimension tables (`dim_payment_types`) are pre-seeded on first startup. The `dim_locations` table should be loaded from the taxi zone lookup CSV produced by earlier pipelines.

## Benchmark Queries

Four benchmark queries live in `clickhouse/queries/` and are executed by `make benchmark-queries`. Each query runs five times so you can observe cold-start vs warm-cache performance.

| File                      | Description                                              |
|---------------------------|----------------------------------------------------------|
| `01-daily-revenue.sql`    | Daily revenue aggregation for January 2024               |
| `02-top-zones.sql`        | Top 10 pickup zones by total revenue (JOIN to dim)       |
| `03-hourly-heatmap.sql`   | Hourly demand heatmap grouped by day of week             |
| `04-complex-revenue.sql`  | Revenue by payment type, borough, and weekday/weekend    |

Results can be saved to `benchmark_results/` for tracking across runs.

## Connecting Metabase to ClickHouse

1. Open Metabase at **http://localhost:3030**.
2. Complete the initial setup wizard.
3. When adding a database, install the ClickHouse driver (Metabase will prompt you or you can add it via the plugin directory).
4. Use these connection settings:
   - **Host:** `clickhouse`
   - **Port:** `8123`
   - **Database:** `nyc_taxi`
   - **User:** `default`
   - **Password:** *(leave blank)*

## Connecting Superset to ClickHouse

1. Open Superset at **http://localhost:8088** and log in with **admin / admin**.
2. Go to **Settings > Database Connections > + Database**.
3. Choose **ClickHouse Connect** as the database type (installed by default in recent Superset images).
4. Enter the SQLAlchemy URI:
   ```
   clickhousedb://default@clickhouse:8123/nyc_taxi
   ```
   If using the `clickhouse-connect` driver:
   ```
   clickhousedb://default@clickhouse/nyc_taxi
   ```
5. Test the connection and save.

## Directory Structure

```
10-serving-comparison/
  docker-compose.yml          # Service definitions
  Makefile                    # Make targets for lifecycle + benchmarks
  README.md                   # This file
  benchmark_results/          # Store benchmark output here
  clickhouse/
    init/
      01-create-tables.sql    # DDL for all Gold-layer tables
      02-load-sample-data.sql # Seed data for dimension tables
    queries/
      01-daily-revenue.sql    # Benchmark query 1
      02-top-zones.sql        # Benchmark query 2
      03-hourly-heatmap.sql   # Benchmark query 3
      04-complex-revenue.sql  # Benchmark query 4
  metabase/                   # Reserved for Metabase config exports
  superset/                   # Reserved for Superset config exports
```

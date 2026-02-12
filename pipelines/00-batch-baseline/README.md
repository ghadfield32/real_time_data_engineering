# Pipeline 00 - Batch Baseline

The simplest pipeline in the project: a containerized **dbt + DuckDB** setup that
runs a full `dbt build` against a static Parquet file.

## Architecture

```
parquet file (data/)  -->  dbt-duckdb container  -->  DuckDB database (dev.duckdb)
```

- **Source**: `yellow_tripdata_2024-01.parquet` mounted at `/data/`
- **Engine**: DuckDB (in-process, via dbt-duckdb adapter)
- **Output**: Fully materialized staging, intermediate, and mart tables inside `dev.duckdb`

## Quick Start

```bash
make up          # Build container and run full dbt build
make dbt-build   # Run dbt build only
make benchmark   # Time the full build
make down        # Tear down containers
```

## dbt Layers

| Layer          | Models                                                   |
|----------------|----------------------------------------------------------|
| Staging        | `stg_yellow_trips`, `stg_payment_types`, `stg_rate_codes`, `stg_taxi_zones` |
| Intermediate   | `int_trip_metrics`, `int_daily_summary`, `int_hourly_patterns` |
| Marts (core)   | `fct_trips`, `dim_dates`, `dim_locations`, `dim_payment_types` |
| Marts (analytics) | `mart_daily_revenue`, `mart_location_performance`, `mart_hourly_demand` |

## Purpose

This pipeline serves as the **baseline** for benchmarking. All other pipelines in the
project are compared against this batch approach to measure latency, throughput, and
resource consumption improvements.

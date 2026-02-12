# Architecture: NYC Taxi Trip Analytics

## Overview

This project transforms raw NYC Yellow Taxi trip data into a dimensional model suitable for analytics. The data flows through three transformation layers before reaching business-ready mart tables.

## Data Sources

### NYC TLC Yellow Taxi Trips (Parquet)
- **Origin**: NYC Taxi & Limousine Commission
- **Period**: January 2024
- **Volume**: ~3 million trip records
- **Format**: Apache Parquet (columnar, compressed)
- **Integration**: DuckDB reads parquet directly via `read_parquet()`; dbt-duckdb's `external_location` makes this seamless with `source()`

### Reference Data (CSV Seeds)
- **taxi_zone_lookup.csv**: 265 TLC Taxi Zones mapping location IDs to borough/zone names
- **payment_type_lookup.csv**: 6 payment method codes
- **rate_code_lookup.csv**: 7 rate code definitions

## Transformation Layers

### Layer 1: Staging (`models/staging/`)
**Purpose**: Create a clean, consistent interface over raw data.

| Model | Source | What It Does |
|-------|--------|-------------|
| `stg_yellow_trips` | Parquet (via source) | Rename to snake_case, cast types, add surrogate key, filter invalid records |
| `stg_taxi_zones` | Seed (via ref) | Rename columns, cast LocationID to integer |
| `stg_payment_types` | Seed (via ref) | Pass through with consistent naming |
| `stg_rate_codes` | Seed (via ref) | Pass through with consistent naming |

**Materialization**: View (no storage cost, always fresh)

### Layer 2: Intermediate (`models/intermediate/`)
**Purpose**: Enrich and aggregate staged data for downstream consumption.

| Model | Upstream | What It Does |
|-------|----------|-------------|
| `int_trip_metrics` | `stg_yellow_trips` | Add duration, speed, cost/mile, tip %, time dims; filter impossible trips |
| `int_daily_summary` | `int_trip_metrics` | Aggregate to one row per day (counts, averages, revenue) |
| `int_hourly_patterns` | `int_trip_metrics` | Aggregate to one row per date+hour |

**Materialization**: View

### Layer 3: Marts (`models/marts/`)
**Purpose**: Serve business-ready data for analysis and reporting.

#### Core (Dimensional Model)

| Model | Type | Grain | Key |
|-------|------|-------|-----|
| `fct_trips` | Fact | One per valid trip | `trip_id` |
| `dim_locations` | Dimension | One per taxi zone | `location_id` |
| `dim_dates` | Dimension | One per day (Jan 2024) | `date_key` |
| `dim_payment_types` | Dimension | One per payment type | `payment_type_id` |

#### Analytics (Pre-Aggregated)

| Model | Grain | Key Business Questions |
|-------|-------|----------------------|
| `mart_daily_revenue` | One per day | Revenue trends, cumulative totals, day-over-day changes |
| `mart_location_performance` | One per pickup zone | Busiest zones, highest revenue areas, common routes |
| `mart_hourly_demand` | One per hour + weekday/weekend | Peak hours, weekday vs weekend patterns |

**Materialization**: Table (optimized for query performance)

## Design Decisions

1. **Parquet over CSV for trip data**: 100MB parquet vs ~1GB CSV. DuckDB reads parquet natively with columnar pushdown.

2. **Seeds for reference data**: Small lookup tables (< 300 rows) are perfect for seeds. They're version-controlled and reproducible.

3. **Surrogate keys**: `dbt_utils.generate_surrogate_key()` creates deterministic hashes since taxi trips lack a natural primary key.

4. **View staging, table marts**: Views keep staging fast and storage-free. Tables make mart queries instant.

5. **Warn severity on relationship tests**: Real-world data has location IDs (264/265) not in the zone lookup. We warn rather than fail.

6. **Date dimension via date_spine**: Generated from dbt_utils rather than from the data itself, ensuring all calendar days are present even if no trips occurred.

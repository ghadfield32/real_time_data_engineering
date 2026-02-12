# Pipeline 04: Redpanda + Flink + Iceberg

A Redpanda variant of Pipeline 01 (Kafka + Flink + Iceberg). This pipeline replaces
Apache Kafka and Confluent Schema Registry with a single Redpanda container, which
provides a Kafka-compatible API with built-in Schema Registry and HTTP Proxy.

This isolates the broker variable for a direct Kafka vs Redpanda comparison while
keeping all other components (Flink, Iceberg, MinIO, dbt) identical.

## Architecture

```
+----------------+     +-------------------+     +-------------------+
|  NYC Yellow    |     |     Redpanda      |     |   Apache Flink    |
|  Taxi Parquet  | --> |  (Kafka-compat)   | --> |   (SQL Client)    |
|  Data Source   |     |   taxi.raw_trips  |     |  Stream → Table   |
+----------------+     +-------------------+     +--------+----------+
                                                          |
                                                          v
+----------------+     +-------------------+     +-------------------+
|    dbt-core    |     |     DuckDB        |     |  Apache Iceberg   |
|   (Gold layer) | <-- | (iceberg_scan)    | <-- |  (on MinIO/S3)    |
|  Analytics     |     |  Query Engine     |     |  Bronze + Silver  |
+----------------+     +-------------------+     +-------------------+
```

### Data Flow

1. **Ingest**: Data Generator reads parquet, produces JSON events to Redpanda topic `taxi.raw_trips`
2. **Bronze**: Flink SQL reads from Redpanda (via Kafka connector), writes raw records to Iceberg `bronze.raw_trips`
3. **Silver**: Flink SQL reads Bronze, applies cleaning/renaming, writes to Iceberg `silver.cleaned_trips`
4. **Gold**: dbt reads Silver Iceberg via DuckDB `iceberg_scan()`, builds dimensional models

### What Changed vs Pipeline 01

- **Kafka + Schema Registry** replaced by a single **Redpanda** container
- `bootstrap.servers` changed from `kafka:9092` to `redpanda:9092`
- Topic creation uses `rpk` CLI instead of `kafka-topics.sh`
- All container names use `p04-` prefix
- Everything else (Flink SQL, Iceberg, MinIO, dbt) is identical

### Services

| Service           | Image                            | Port(s)      | Purpose                            |
|-------------------|----------------------------------|--------------|------------------------------------|
| redpanda          | redpandadata/redpanda:latest     | 19092, 18081, 18082, 9644 | Kafka-compatible streaming + Schema Registry |
| flink-jobmanager  | flink:1.20-java17                | 8081         | Flink cluster coordinator          |
| flink-taskmanager | flink:1.20-java17                | -            | Flink compute workers              |
| minio             | minio/minio:latest               | 9000, 9001   | S3-compatible object storage       |
| mc-init           | minio/mc:latest                  | -            | Bucket initialization              |
| dbt               | python:3.12-slim + dbt-duckdb    | -            | Gold layer transformations         |
| data-generator    | python:3.12-slim                 | -            | Taxi event producer                |

### Port Reference

| Port  | Service              | Protocol     |
|-------|----------------------|--------------|
| 19092 | Redpanda Kafka API   | Kafka        |
| 18081 | Redpanda Schema Reg. | HTTP         |
| 18082 | Redpanda Pandaproxy  | HTTP         |
| 9644  | Redpanda Admin API   | HTTP         |
| 8081  | Flink Dashboard      | HTTP         |
| 9000  | MinIO S3 API         | HTTP         |
| 9001  | MinIO Console        | HTTP         |

## Quick Start

```bash
# 1. Start infrastructure
make up

# 2. Create Redpanda topics
make create-topics

# 3. Generate taxi trip events
make generate

# 4. Submit Flink SQL processing jobs
make process

# 5. Wait for Flink to process data (~30s for full dataset)
sleep 30

# 6. Run dbt transformations on Silver data
make dbt-build

# 7. Tear down when done
make down
```

## Full Benchmark

Run the complete end-to-end pipeline with timing:

```bash
make benchmark
```

This will start all services, generate data, process through Flink, run dbt, and
report total elapsed time. Results are saved to `benchmark_results/latest.json`.

## Flink SQL Layers

### Bronze Layer (`03-bronze-raw-trips.sql`)
- Creates an Iceberg table with raw column names preserved from Redpanda
- Parses timestamp strings to TIMESTAMP type
- Continuous INSERT INTO from the Kafka source table

### Silver Layer (`04-silver-cleaned-trips.sql`)
- Renames columns to snake_case conventions
- Applies data quality filters (nulls, negative fares, date range)
- Generates surrogate key via MD5 hash
- Computes enrichment columns: duration_minutes, avg_speed_mph, cost_per_mile, tip_percentage

## dbt Project

The dbt project reads the Silver Iceberg table via DuckDB's `iceberg_scan()` function
and builds a standard dimensional model:

- **Staging**: Simple passthrough (Flink already cleaned the data)
- **Intermediate**: Trip metrics, daily summaries, hourly patterns
- **Marts/Core**: `fct_trips`, `dim_locations`, `dim_dates`, `dim_payment_types`
- **Marts/Analytics**: `mart_daily_revenue`, `mart_hourly_demand`, `mart_location_performance`

## Monitoring

- **Flink Dashboard**: http://localhost:8081
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Redpanda Admin**: http://localhost:9644
- **Schema Registry**: http://localhost:18081/subjects

## Makefile Targets

```bash
make help            # Show all available targets
make up              # Start infrastructure
make down            # Stop and remove volumes
make create-topics   # Create Redpanda topics
make generate        # Produce events to Redpanda
make process         # Submit all Flink SQL jobs
make dbt-build       # Run dbt transformations
make benchmark       # Full E2E benchmark
make logs            # Tail all service logs
make status          # Show service and job status
```

## Prerequisites

- Docker and Docker Compose v2
- ~4 GB available RAM (Flink + Redpanda + MinIO)
- NYC Yellow Taxi parquet data at `../../data/yellow_tripdata_2024-01.parquet`

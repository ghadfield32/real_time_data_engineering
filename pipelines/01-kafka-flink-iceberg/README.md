# Pipeline 01: Kafka + Flink + Iceberg

The 2026 industry standard streaming pipeline. This is the reference implementation for
real-time data engineering with Apache Kafka, Apache Flink, and Apache Iceberg.

## Architecture

```
+----------------+     +-------------------+     +-------------------+
|  NYC Yellow    |     |    Apache Kafka   |     |   Apache Flink    |
|  Taxi Parquet  | --> |   (KRaft mode)    | --> |   (SQL Client)    |
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

1. **Ingest**: Data Generator reads parquet, produces JSON events to Kafka topic `taxi.raw_trips`
2. **Bronze**: Flink SQL reads from Kafka, writes raw records to Iceberg `bronze.raw_trips`
3. **Silver**: Flink SQL reads Bronze, applies cleaning/renaming, writes to Iceberg `silver.cleaned_trips`
4. **Gold**: dbt reads Silver Iceberg via DuckDB `iceberg_scan()`, builds dimensional models

### Services

| Service           | Image                                 | Port(s)     | Purpose                        |
|-------------------|---------------------------------------|-------------|--------------------------------|
| kafka             | apache/kafka:latest                   | 9092        | Event streaming (KRaft mode)   |
| schema-registry   | confluentinc/cp-schema-registry:7.6.0 | 8085        | Schema management              |
| flink-jobmanager  | flink:1.20-java17                     | 8081        | Flink cluster coordinator      |
| flink-taskmanager | flink:1.20-java17                     | -           | Flink compute workers          |
| minio             | minio/minio:latest                    | 9000, 9001  | S3-compatible object storage   |
| mc-init           | minio/mc:latest                       | -           | Bucket initialization          |
| dbt               | python:3.12-slim + dbt-duckdb         | -           | Gold layer transformations     |
| data-generator    | python:3.12-slim                      | -           | Taxi event producer            |

## Quick Start

```bash
# 1. Start infrastructure
make up

# 2. Create Kafka topics
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
- Creates an Iceberg table with raw column names preserved from Kafka
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
- **Schema Registry**: http://localhost:8085/subjects

## Makefile Targets

```bash
make help            # Show all available targets
make up              # Start infrastructure
make down            # Stop and remove volumes
make create-topics   # Create Kafka topics
make generate        # Produce events to Kafka
make process         # Submit all Flink SQL jobs
make dbt-build       # Run dbt transformations
make benchmark       # Full E2E benchmark
make logs            # Tail all service logs
make status          # Show service and job status
```

## Prerequisites

- Docker and Docker Compose v2
- ~4 GB available RAM (Flink + Kafka + MinIO)
- NYC Yellow Taxi parquet data at `../../data/yellow_tripdata_2024-01.parquet`

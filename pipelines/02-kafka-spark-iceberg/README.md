# Pipeline 02: Kafka + Spark + Iceberg

Spark-centric streaming pipeline for NYC Yellow Taxi trip data.

## Architecture

```
Data Generator --> Kafka (KRaft) --> Spark Structured Streaming --> Iceberg (MinIO)
                                                                        |
                                                                   dbt (DuckDB)
                                                                        |
                                                                   Analytics Marts
```

### Components

| Service          | Image                    | Purpose                                   |
|------------------|--------------------------|-------------------------------------------|
| `kafka`          | `apache/kafka:latest`    | Event streaming (KRaft single-node)       |
| `spark-master`   | `bitnami/spark:3.5`      | Spark cluster master                      |
| `spark-worker`   | `bitnami/spark:3.5`      | Spark cluster worker (2 GB)               |
| `minio`          | `minio/minio:latest`     | S3-compatible object storage for Iceberg  |
| `mc-init`        | `minio/mc:latest`        | Creates the `warehouse` bucket on startup |
| `dbt`            | Python 3.12 + dbt-duckdb | Transforms Silver Iceberg into Gold marts |
| `data-generator` | Python 3.12              | Produces taxi trip events to Kafka        |

### Data Flow

1. **Data Generator** reads parquet data and produces JSON events to Kafka topic `taxi.raw_trips`
2. **Bronze Ingest** (PySpark Structured Streaming) reads from Kafka, parses JSON, writes to `warehouse.bronze.raw_trips` Iceberg table
3. **Silver Transform** (PySpark batch) reads Bronze, applies cleansing/enrichment/metrics, writes to `warehouse.silver.cleaned_trips` Iceberg table
4. **dbt** (DuckDB adapter) reads Silver Iceberg table via `iceberg_scan()`, builds staging, intermediate, and mart models

## Quick Start

```bash
# 1. Start infrastructure
make up

# 2. Generate events (all ~3M taxi trips)
make generate

# 3. Run Spark processing (Bronze + Silver)
make process

# 4. Run dbt build (seed + models + tests)
make dbt-build

# 5. Check status
make status

# 6. Tear down
make down
```

## Makefile Targets

| Target            | Description                                     |
|-------------------|-------------------------------------------------|
| `up`              | Start all core services                         |
| `down`            | Stop and remove containers + volumes            |
| `generate`        | Produce all taxi events to Kafka                |
| `generate-sample` | Produce 10K sample events                       |
| `process`         | Run Bronze + Silver Spark jobs                  |
| `process-bronze`  | Run Bronze ingest only                          |
| `process-silver`  | Run Silver transform only                       |
| `dbt-build`       | Install deps, seed, build all dbt models/tests  |
| `dbt-test`        | Run dbt tests only                              |
| `benchmark`       | Full end-to-end benchmark run                   |
| `logs`            | Tail logs for all services                      |
| `status`          | Show container health and Kafka topics          |
| `clean`           | Remove containers, volumes, and result files    |
| `topics`          | Create Kafka topics                             |

## Spark Jobs

### Bronze Ingest (`spark/jobs/bronze_ingest.py`)

- PySpark Structured Streaming job
- Reads from Kafka topic `taxi.raw_trips`
- Parses JSON value column with explicit schema
- Preserves Kafka metadata (timestamp, partition, offset)
- Writes to Iceberg table `warehouse.bronze.raw_trips`
- Uses `trigger(availableNow=True)` for batch-style benchmark processing

### Silver Transform (`spark/jobs/silver_transform.py`)

- PySpark batch job
- Reads Bronze Iceberg table
- Applies transformations matching shared dbt models:
  - Column renaming (VendorID -> vendor_id, etc.)
  - Type casting to proper types
  - Null/negative/date-range filtering
  - Surrogate key generation via MD5
  - Metric computation (duration, speed, cost per mile, tip percentage)
  - Time dimension extraction (date, hour, day of week, is_weekend)
  - Impossible trip filtering (duration < 1 or > 720 min, speed > 100 mph)
- Writes to `warehouse.silver.cleaned_trips` in overwrite mode

## dbt Project

The dbt layer uses `dbt-duckdb` reading the Silver Iceberg table via `iceberg_scan()`. This keeps the dbt layer consistent across pipelines.

### Model Layers

- **Staging**: `stg_yellow_trips`, `stg_taxi_zones`, `stg_payment_types`, `stg_rate_codes`
- **Intermediate**: `int_trip_metrics`, `int_daily_summary`, `int_hourly_patterns`
- **Core Marts**: `fct_trips`, `dim_locations`, `dim_dates`, `dim_payment_types`
- **Analytics Marts**: `mart_daily_revenue`, `mart_hourly_demand`, `mart_location_performance`

## Ports

| Service      | Port  | Description       |
|--------------|-------|-------------------|
| Kafka        | 9092  | Bootstrap server  |
| Spark Master | 8080  | Web UI            |
| Spark Master | 7077  | Cluster endpoint  |
| MinIO API    | 9000  | S3 API            |
| MinIO UI     | 9001  | Web console       |

## Credentials

| Service | Username    | Password    |
|---------|-------------|-------------|
| MinIO   | minioadmin  | minioadmin  |

# Pipeline 03 - Kafka + RisingWave

The simplest streaming pipeline in the project. RisingWave is a streaming database that consumes directly from Kafka and maintains incrementally-updated materialized views -- no separate storage layer (MinIO/Iceberg) needed.

## Architecture

```
Parquet File
    |
    v
[Data Generator] --> [Kafka] --> [RisingWave] --> [dbt (postgres)]
                     (broker)   (streaming DB)    (analytics layer)
```

**Components:**
- **Kafka** (KRaft mode) -- message broker for taxi trip events
- **RisingWave** (playground mode) -- streaming database with PostgreSQL wire protocol
- **Data Generator** -- reads parquet, produces JSON events to Kafka
- **dbt** (dbt-postgres) -- builds analytical models on top of RisingWave MVs

## How It Works

1. **Ingest**: Data generator reads NYC taxi parquet and produces JSON events to `taxi.raw_trips` Kafka topic
2. **Stream**: RisingWave creates a Kafka SOURCE and continuously consumes events
3. **Bronze**: `bronze_raw_trips` MV renames columns and casts timestamps
4. **Silver**: `silver_cleaned_trips` MV applies quality filters, computes metrics (duration, speed, cost per mile, tip percentage), and adds time dimensions
5. **Analytics**: dbt builds fact/dimension tables and analytics marts on top of the silver MV

RisingWave materialized views are **incrementally maintained** -- they update automatically as new Kafka events arrive, with no batch reprocessing needed.

## Quick Start

```bash
# Start infrastructure (Kafka + RisingWave)
make up

# Create streaming objects (Kafka source + materialized views)
make process

# Generate taxi events into Kafka
make generate

# Run dbt build (analytics layer)
make dbt-build

# Check status and row counts
make status

# Tear down everything
make down
```

## Ports

| Service    | Port | Description              |
|------------|------|--------------------------|
| Kafka      | 9092 | Bootstrap server         |
| RisingWave | 4566 | PostgreSQL-compatible SQL |
| RisingWave | 5691 | Dashboard UI             |

## Connecting to RisingWave

```bash
# Via psql (from host)
PGPASSWORD= psql -h localhost -p 4566 -U root -d dev

# Check materialized view counts
SELECT count(*) FROM bronze_raw_trips;
SELECT count(*) FROM silver_cleaned_trips;
```

## Make Targets

| Target     | Description                                      |
|------------|--------------------------------------------------|
| `up`       | Start Kafka + RisingWave, create topics          |
| `down`     | Tear down all containers and volumes             |
| `generate` | Produce taxi events into Kafka                   |
| `process`  | Submit RisingWave SQL (source + MVs)             |
| `dbt-build`| Run dbt build against RisingWave                 |
| `benchmark`| Full end-to-end timed run                        |
| `logs`     | Tail logs for all services                       |
| `status`   | Show containers and MV row counts                |

## Key Differences from Other Pipelines

- **No MinIO/S3**: RisingWave manages its own state storage
- **No Iceberg**: Data lives in RisingWave materialized views, not table format files
- **No Flink/Spark**: RisingWave handles both stream processing and SQL queries
- **PostgreSQL compatible**: Uses `dbt-postgres` adapter directly
- **Fewest containers**: Only Kafka + RisingWave needed for the streaming layer

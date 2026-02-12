# Pipeline 06 - Redpanda + RisingWave

A Redpanda variant of [Pipeline 03 (Kafka + RisingWave)](../03-kafka-risingwave/). The **only** infrastructure change is replacing Apache Kafka with Redpanda as the message broker. RisingWave processing, dbt analytics, and data generation remain identical.

This pipeline isolates the broker variable for direct comparison between Kafka and Redpanda while keeping all other components constant.

## Architecture

```
Parquet File
    |
    v
[Data Generator] --> [Redpanda] --> [RisingWave] --> [dbt (postgres)]
                     (broker)      (streaming DB)    (analytics layer)
```

**Components (only 4 containers):**
- **Redpanda** -- Kafka-compatible streaming platform (single node, no JVM, no ZooKeeper)
- **RisingWave** (playground mode) -- streaming database with PostgreSQL wire protocol
- **Data Generator** -- reads parquet, produces JSON events to Redpanda
- **dbt** (dbt-postgres) -- builds analytical models on top of RisingWave MVs

## Simplicity

This is one of the simplest streaming pipelines possible: only 2 main services (Redpanda + RisingWave) plus the dbt analytics layer and data generator. Redpanda's single-binary design means no separate ZooKeeper or KRaft controller -- just start the broker.

## What Changed from Pipeline 03

| Aspect | Pipeline 03 | Pipeline 06 |
|--------|-------------|-------------|
| Broker | Apache Kafka (KRaft) | Redpanda |
| Broker image | `apache/kafka:latest` | `redpandadata/redpanda:latest` |
| Topic creation | `kafka-topics.sh` | `rpk topic create` |
| Bootstrap server | `kafka:9092` | `redpanda:9092` |
| RisingWave SQL | `properties.bootstrap.server = 'kafka:9092'` | `properties.bootstrap.server = 'redpanda:9092'` |
| Everything else | Identical | Identical |

## How It Works

1. **Ingest**: Data generator reads NYC taxi parquet and produces JSON events to `taxi.raw_trips` Redpanda topic
2. **Stream**: RisingWave creates a Kafka-compatible SOURCE and continuously consumes events from Redpanda
3. **Bronze**: `bronze_raw_trips` MV renames columns and casts timestamps
4. **Silver**: `silver_cleaned_trips` MV applies quality filters, computes metrics (duration, speed, cost per mile, tip percentage), and adds time dimensions
5. **Analytics**: dbt builds fact/dimension tables and analytics marts on top of the silver MV

RisingWave materialized views are **incrementally maintained** -- they update automatically as new events arrive, with no batch reprocessing needed.

## Quick Start

```bash
# Start infrastructure (Redpanda + RisingWave)
make up

# Create streaming objects (source + materialized views)
make process

# Generate taxi events into Redpanda
make generate

# Run dbt build (analytics layer)
make dbt-build

# Check status and row counts
make status

# Tear down everything
make down
```

## Ports

| Service    | Port  | Description              |
|------------|-------|--------------------------|
| Redpanda   | 19092 | Kafka API (external)     |
| Redpanda   | 18081 | Schema Registry          |
| Redpanda   | 18082 | HTTP Proxy (Pandaproxy)  |
| Redpanda   | 9644  | Admin API                |
| RisingWave | 4566  | PostgreSQL-compatible SQL |
| RisingWave | 5691  | Dashboard UI             |

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
| `up`       | Start Redpanda + RisingWave, create topics       |
| `down`     | Tear down all containers and volumes             |
| `generate` | Produce taxi events into Redpanda                |
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
- **Redpanda over Kafka**: Single binary, no JVM overhead, Kafka API compatible

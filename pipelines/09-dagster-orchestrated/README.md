# Pipeline 09: Dagster Orchestrated

Wraps Pipeline 01 (Kafka + Flink + Iceberg) with **Dagster** for asset-centric workflow orchestration.

## Architecture

```
Dagster (Orchestrator)
  |
  v
Kafka (KRaft) --> Flink SQL --> Iceberg (MinIO) --> dbt (DuckDB)
  ^                                                      |
  |                                                      v
Data Generator                                    Analytics Marts
```

Dagster provides an asset-centric orchestration model where each pipeline step is defined as a software-defined asset with explicit dependencies. The asset graph provides full lineage visibility through the Dagster UI.

## Services

| Service            | Container Name        | Port(s)        | Description                          |
|--------------------|-----------------------|----------------|--------------------------------------|
| Kafka              | p09-kafka             | 9092           | Event streaming (KRaft mode)         |
| Schema Registry    | p09-schema-registry   | 8085           | Confluent Schema Registry            |
| MinIO              | p09-minio             | 9000, 9001     | S3-compatible object storage         |
| MinIO Init         | p09-mc-init           | -              | Creates warehouse bucket             |
| Flink JobManager   | p09-flink-jobmanager  | 8081           | Flink cluster coordinator            |
| Flink TaskManager  | p09-flink-taskmanager | -              | Flink worker                         |
| dbt                | p09-dbt               | -              | DuckDB-based transformations         |
| Data Generator     | p09-data-generator    | -              | NYC taxi trip event producer         |
| Dagster Webserver  | p09-dagster-webserver | 3000           | Dagster UI                           |
| Dagster Daemon     | p09-dagster-daemon    | -              | Scheduler + sensor runner            |
| Dagster PostgreSQL | p09-dagster-postgres  | -              | Dagster metadata store               |

## Quick Start

```bash
# Start all services
make up

# Run pipeline manually
make create-topics
make generate
make process
make dbt-build

# Or trigger via Dagster UI
make dagster-ui   # http://localhost:3000

# Full benchmark
make benchmark

# Stop and clean up
make down
```

## Dagster Assets

The Dagster definitions (`dagster/definitions.py`) define the pipeline as a chain of software-defined assets:

```
kafka_topics -> generate_events -> flink_processing -> dbt_build
```

1. **kafka_topics** - Create Kafka topics for taxi data
2. **generate_events** - Produce NYC taxi trip events to Kafka
3. **flink_processing** - Submit Flink Bronze + Silver SQL jobs
4. **dbt_build** - Wait 60s for processing, then run dbt build

## Why Dagster?

- **Asset-centric**: Pipeline defined as software-defined assets with lineage
- **Type-safe**: Strong typing and metadata support for assets
- **Observable**: Built-in asset materialization tracking and monitoring
- **Developer-friendly**: Python-native with excellent testing support
- **Modern UI**: Asset graph, run timeline, and partition management

# Pipeline 07: Kestra Orchestrated

Wraps Pipeline 01 (Kafka + Flink + Iceberg) with **Kestra** for YAML-first workflow orchestration.

## Architecture

```
Kestra (Orchestrator)
  |
  v
Kafka (KRaft) --> Flink SQL --> Iceberg (MinIO) --> dbt (DuckDB)
  ^                                                      |
  |                                                      v
Data Generator                                    Analytics Marts
```

Kestra provides a declarative YAML-based workflow definition that orchestrates the entire pipeline lifecycle: topic creation, data generation, Flink job submission, and dbt transformations.

## Services

| Service            | Container Name     | Port(s)        | Description                          |
|--------------------|--------------------|----------------|--------------------------------------|
| Kafka              | p07-kafka          | 9092           | Event streaming (KRaft mode)         |
| Schema Registry    | p07-schema-registry| 8085           | Confluent Schema Registry            |
| MinIO              | p07-minio          | 9000, 9001     | S3-compatible object storage         |
| MinIO Init         | p07-mc-init        | -              | Creates warehouse bucket             |
| Flink JobManager   | p07-flink-jobmanager| 8081          | Flink cluster coordinator            |
| Flink TaskManager  | p07-flink-taskmanager| -             | Flink worker                         |
| dbt                | p07-dbt            | -              | DuckDB-based transformations         |
| Data Generator     | p07-data-generator | -              | NYC taxi trip event producer         |
| Kestra             | p07-kestra         | 8083           | YAML-first workflow orchestration    |
| Kestra PostgreSQL  | p07-kestra-postgres| -              | Kestra metadata store                |

## Quick Start

```bash
# Start all services
make up

# Run pipeline manually
make create-topics
make generate
make process
make dbt-build

# Or trigger via Kestra UI
make kestra-ui   # http://localhost:8083

# Full benchmark
make benchmark

# Stop and clean up
make down
```

## Kestra Flow

The Kestra flow (`kestra/flows/taxi_pipeline.yml`) defines the pipeline as a sequence of tasks:

1. **create_topics** - Create Kafka topics for taxi data
2. **generate_events** - Produce NYC taxi trip events to Kafka
3. **submit_flink_bronze** - Submit Flink Bronze layer SQL jobs
4. **submit_flink_silver** - Submit Flink Silver layer SQL jobs
5. **wait_for_processing** - Wait 60s for Flink to process events
6. **dbt_build** - Run dbt build for Gold layer analytics

## Why Kestra?

- **YAML-first**: Entire pipeline defined declaratively in YAML
- **Built-in UI**: Visual workflow editor and execution monitoring
- **Docker-native**: Tasks run in isolated Docker containers
- **Event-driven**: Supports triggers, schedules, and webhooks
- **Versioned workflows**: Flow definitions stored as code

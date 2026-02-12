# Pipeline 08: Airflow Orchestrated

Wraps Pipeline 01 (Kafka + Flink + Iceberg) with **Apache Airflow** for DAG-based workflow orchestration.

## Architecture

```
Airflow (Orchestrator)
  |
  v
Kafka (KRaft) --> Flink SQL --> Iceberg (MinIO) --> dbt (DuckDB)
  ^                                                      |
  |                                                      v
Data Generator                                    Analytics Marts
```

Airflow provides a Python-based DAG definition that orchestrates the entire pipeline lifecycle through BashOperators and sensors: topic creation, data generation, Flink job submission, processing wait, and dbt transformations.

## Services

| Service            | Container Name       | Port(s)        | Description                          |
|--------------------|----------------------|----------------|--------------------------------------|
| Kafka              | p08-kafka            | 9092           | Event streaming (KRaft mode)         |
| Schema Registry    | p08-schema-registry  | 8085           | Confluent Schema Registry            |
| MinIO              | p08-minio            | 9000, 9001     | S3-compatible object storage         |
| MinIO Init         | p08-mc-init          | -              | Creates warehouse bucket             |
| Flink JobManager   | p08-flink-jobmanager | 8081           | Flink cluster coordinator            |
| Flink TaskManager  | p08-flink-taskmanager| -              | Flink worker                         |
| dbt                | p08-dbt              | -              | DuckDB-based transformations         |
| Data Generator     | p08-data-generator   | -              | NYC taxi trip event producer         |
| Airflow Webserver  | p08-airflow-webserver| 8084           | Airflow UI (admin/admin)             |
| Airflow Scheduler  | p08-airflow-scheduler| -              | DAG scheduler                        |
| Airflow Init       | p08-airflow-init     | -              | DB migration + user creation         |
| Airflow PostgreSQL | p08-airflow-postgres | -              | Airflow metadata store               |

## Quick Start

```bash
# Start all services
make up

# Run pipeline manually
make create-topics
make generate
make process
make dbt-build

# Or trigger via Airflow UI
make airflow-ui   # http://localhost:8084 (admin/admin)

# Full benchmark
make benchmark

# Stop and clean up
make down
```

## Airflow DAG

The DAG (`airflow/dags/taxi_pipeline_dag.py`) defines the pipeline as a task chain:

```
create_kafka_topics >> generate_events >> submit_flink_bronze >> submit_flink_silver >> wait_for_processing >> dbt_build
```

1. **create_kafka_topics** - Create Kafka topics via docker exec
2. **generate_events** - Produce NYC taxi trip events to Kafka
3. **submit_flink_bronze** - Submit Flink Bronze layer SQL jobs
4. **submit_flink_silver** - Submit Flink Silver layer SQL jobs
5. **wait_for_processing** - TimeDeltaSensor waits 60s for Flink processing
6. **dbt_build** - Run dbt build for Gold layer analytics

## Why Airflow?

- **Industry standard**: Most widely adopted workflow orchestrator
- **Python-native**: DAGs defined in Python with full language capabilities
- **Rich ecosystem**: Extensive provider packages and community plugins
- **Mature UI**: Task logs, Gantt charts, graph view, and calendar
- **Battle-tested**: Proven at scale across thousands of organizations

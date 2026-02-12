# Pipeline 05: Redpanda + Spark + Iceberg

This pipeline is a **Redpanda variant** of [Pipeline 02 (Kafka + Spark + Iceberg)](../02-kafka-spark-iceberg/). The only architectural change is replacing Apache Kafka with [Redpanda](https://redpanda.com/) as the streaming broker.

## Architecture

```
Redpanda --> Spark Structured Streaming --> Iceberg (MinIO) --> dbt (DuckDB)
```

- **Broker**: Redpanda (Kafka-compatible API, no JVM/ZooKeeper)
- **Stream processing**: Apache Spark 3.5 (Structured Streaming)
- **Table format**: Apache Iceberg on MinIO (S3-compatible)
- **Analytics layer**: dbt with DuckDB adapter reading Iceberg tables via `iceberg_scan()`

## Why Redpanda?

Redpanda is a Kafka-compatible streaming platform written in C++. It requires no JVM and no ZooKeeper, resulting in simpler operations and potentially lower latency. By keeping everything else identical to Pipeline 02 (same Spark jobs, same Iceberg tables, same dbt models), this pipeline isolates the broker as the single variable for comparison.

## Quick Start

```bash
# Start all services
make up

# Generate sample data (10k events)
make generate-sample

# Run Spark Bronze + Silver processing
make process

# Run dbt build
make dbt-build

# Full end-to-end benchmark
make benchmark
```

## Services

| Service        | Container       | Ports                          |
|----------------|-----------------|--------------------------------|
| Redpanda       | p05-redpanda    | 19092, 18081, 18082, 9644      |
| MinIO          | p05-minio       | 9000 (API), 9001 (Console)     |
| Spark Master   | p05-spark-master| 8080 (UI), 7077 (RPC)          |
| Spark Worker   | p05-spark-worker| —                              |
| dbt            | p05-dbt         | —                              |
| Data Generator | p05-data-generator | — (profile: generate)       |

## Key Differences from Pipeline 02

| Aspect              | Pipeline 02               | Pipeline 05                |
|---------------------|---------------------------|----------------------------|
| Broker              | Apache Kafka (KRaft)      | Redpanda                   |
| Broker image        | `apache/kafka:latest`     | `redpandadata/redpanda:latest` |
| Topic management    | `kafka-topics.sh`         | `rpk topic`                |
| JVM required        | Yes (Kafka)               | No                         |
| External port       | 9092                      | 19092                      |
| Bootstrap servers   | `kafka:9092`              | `redpanda:9092`            |

All other components (Spark jobs, Iceberg storage, dbt models) are identical.

## Configuration

The Spark Bronze ingest job reads the broker address from the `BROKER_URL` environment variable, defaulting to `redpanda:9092`. This is set in `docker-compose.yml` on the `spark-master` and `spark-worker` services.

## Makefile Targets

| Target            | Description                                |
|-------------------|--------------------------------------------|
| `make up`         | Start core services and create topics      |
| `make down`       | Stop and remove all containers + volumes   |
| `make clean`      | Full cleanup including benchmark results   |
| `make topics`     | Create Redpanda topics                     |
| `make generate`   | Produce all taxi events to Redpanda        |
| `make generate-sample` | Produce 10k sample events             |
| `make process`    | Run Bronze + Silver Spark jobs             |
| `make process-bronze` | Run Bronze ingest only                 |
| `make process-silver` | Run Silver transform only              |
| `make dbt-build`  | Install deps, seed, and build dbt models   |
| `make dbt-test`   | Run dbt tests                              |
| `make benchmark`  | Full end-to-end benchmark run              |
| `make status`     | Show container status and Redpanda topics  |
| `make logs`       | Tail logs for all services                 |

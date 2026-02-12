# Pipeline 11: Observability Stack

Pipeline 01 (Kafka + Flink + Iceberg) with data observability powered by **Elementary** (dbt package) and **Soda Core** (standalone quality checks).

## Architecture

```
Kafka (KRaft) --> Flink SQL --> Iceberg (MinIO) --> dbt (DuckDB) --> Elementary
                                                                  \-> Soda Core
```

This pipeline extends Pipeline 01 with two complementary observability tools:

- **Elementary** is a dbt package that runs inside dbt and monitors test results, data freshness, volume anomalies, and schema drift over time. It stores observability metadata in dbt models and can generate HTML reports.
- **Soda Core** is a standalone data quality tool that runs independently of dbt. It executes declarative check files against each medallion layer (Bronze, Silver, Gold) to validate row counts, duplicates, value ranges, and schema conformance.

### What Elementary Monitors

| Capability | Description |
|---|---|
| Test results | Tracks pass/fail history of all dbt tests across runs |
| Freshness | Detects stale tables that have not been updated recently |
| Volume anomalies | Alerts when row counts deviate from historical patterns |
| Schema drift | Detects unexpected column additions, removals, or type changes |

### What Soda Core Checks

| Layer | Checks |
|---|---|
| **Bronze** | Row count > 0, schema validation (timestamp/double types) |
| **Silver** | Row count range, no duplicate trip IDs, average fare range, invalid duration %, max duration, no negative fares |
| **Gold** | 31 days in January, positive revenue all days, minimum trip counts, fact table volume, location dimension populated, no duplicate location IDs |

## Services

| Service | Image | Container | Ports |
|---|---|---|---|
| Kafka (KRaft) | apache/kafka:latest | p11-kafka | 9092 |
| Schema Registry | confluentinc/cp-schema-registry:7.6.0 | p11-schema-registry | 8085 |
| MinIO | minio/minio:latest | p11-minio | 9000, 9001 |
| MinIO Init | minio/mc:latest | p11-mc-init | - |
| Flink JobManager | flink:1.20-java17 | p11-flink-jobmanager | 8081 |
| Flink TaskManager | flink:1.20-java17 | p11-flink-taskmanager | - |
| dbt (DuckDB) | custom (dbt.Dockerfile) | p11-dbt | - |
| Data Generator | custom (Dockerfile) | p11-data-generator | - |
| Soda Core | custom (python:3.12-slim) | p11-soda | - |

## Quick Start

```bash
# 1. Start infrastructure
make up

# 2. Create Kafka topics
make create-topics

# 3. Produce taxi events
make generate

# 4. Submit Flink SQL jobs (Bronze + Silver layers)
make process

# 5. Run dbt build (staging -> intermediate -> marts + Elementary)
make dbt-build

# 6. Run Soda Core quality checks against all layers
make soda-check

# 7. Generate Elementary observability report
make elementary-report
```

Or run the full end-to-end benchmark:

```bash
make benchmark
```

## Project Structure

```
11-observability-stack/
├── docker-compose.yml          # All services with p11- prefix
├── Makefile                    # Orchestration commands
├── README.md
├── flink/
│   └── sql/                    # Flink SQL jobs (identical to pipeline 01)
│       ├── 01-create-kafka-source.sql
│       ├── 02-create-iceberg-catalog.sql
│       ├── 03-bronze-raw-trips.sql
│       └── 04-silver-cleaned-trips.sql
├── dbt_project/                # dbt project with Elementary package
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── packages.yml            # Includes elementary-data/elementary
│   ├── models/
│   │   ├── sources/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   ├── macros/
│   ├── tests/
│   └── seeds/
├── elementary/
│   └── elementary_config.yml   # Elementary observability settings
├── soda/
│   ├── Dockerfile              # Soda Core container
│   ├── configuration.yml       # DuckDB data source config
│   └── checks/
│       ├── bronze_checks.yml   # Bronze layer quality checks
│       ├── silver_checks.yml   # Silver layer quality checks
│       └── gold_checks.yml     # Gold layer quality checks
├── benchmark_results/
└── observability_results/
```

## Makefile Targets

| Target | Description |
|---|---|
| `up` | Start all infrastructure services |
| `down` | Stop all services and remove volumes |
| `create-topics` | Create Kafka topics |
| `generate` | Produce taxi events to Kafka |
| `process` | Submit Flink SQL jobs (Bronze + Silver) |
| `dbt-build` | Run dbt build with Elementary |
| `soda-check` | Run Soda Core quality checks |
| `elementary-report` | Generate Elementary observability report |
| `benchmark` | Full E2E pipeline run |
| `logs` | Tail all logs |
| `status` | Show service status |
| `help` | Show available targets |

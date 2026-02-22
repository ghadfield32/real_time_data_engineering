# Pipeline Comparison Report

Auto-generated from benchmark results (24 pipelines in results.csv).

**Status**: 22 benchmarked (PASS), 2 pending (READY)

## Table of Contents

### Tiered Comparison
- [Tier 1: Core Pipelines (P00-P06)](#tier-1-core-pipeline-comparison)
- [Tier 2: Orchestration (P07-P09)](#tier-2-orchestration-comparison-kestra--airflow--dagster)
- [Tier 3: Serving Layer (P10)](#tier-3-serving-layer-clickhouse)
- [Tier 4: Observability (P11)](#tier-4-observability-elementary--soda-core)
- [Tier 5: CDC Pipelines (P12, P23)](#tier-5-cdc-pipelines-debezium--full-stack-capstone)
- [Tier 6: Table Formats (P13, P22)](#tier-6-alternative-table-formats-delta-lake--hudi)
- [Tier 7: Streaming SQL (P14)](#tier-7-alternative-streaming-sql-materialize)
- [Tier 8: Lightweight (P15, P20)](#tier-8-lightweight-stream-processors-kafka-streams--bytewax)
- [Tier 9: OLAP Engines (P16, P17)](#tier-9-olap-engines-pinot--druid)
- [Tier 10: Orchestrators (P18, P19)](#tier-10-additional-orchestrators-prefect--mage-ai)
- [Tier 11: ML Feature Store (P21)](#tier-11-ml-feature-store-feast)

### Cross-Cutting Comparisons
- [Table Format: Iceberg vs Delta Lake vs Hudi](#table-format-comparison-iceberg-vs-delta-lake-vs-hudi)
- [OLAP: ClickHouse vs Pinot vs Druid](#olap-engine-comparison-clickhouse-vs-pinot-vs-druid)
- [All Orchestrators](#all-orchestrators-kestra-vs-airflow-vs-dagster-vs-prefect-vs-mage)
- [Streaming SQL: RisingWave vs Materialize](#streaming-sql-risingwave-vs-materialize)
- [Lightweight: Kafka Streams vs Bytewax](#lightweight-stream-processors-kafka-streams-vs-bytewax)
- [CDC: Debezium vs Full Stack](#cdc-comparison-debezium-standalone-vs-full-stack-capstone)

### Summary
- [Overall Recommendations](#overall-recommendations)

## Tier 1: Core Pipeline Comparison

Pipelines P00-P06 form the core matrix comparing brokers (Kafka vs Redpanda) and processors (Flink vs Spark vs RisingWave).

| Pipeline | Ingestion | Processing | Storage | Services | Startup (s) | Ingestion (evt/s) | Bronze (s) | Silver (s) | Total Processing (s) | Memory (MB) | Status |
|----------|-----------|------------|---------|----------|-------------|-------------------|------------|------------|----------------------|-------------|--------|
| P00 Batch Baseline (dbt only) | - | - | - | 4 | 62 | - | - | - | 89 | - | PASS |
| P01 Kafka + Flink + Iceberg | Kafka | Flink | Iceberg | 8 | 19 | 24 | - | - | 151 | - | PASS |
| P02 Kafka + Spark + Iceberg | Kafka | Spark | Iceberg | 9 | 19 | 26 | - | - | 93 | - | PASS |
| P03 Kafka + RisingWave | Kafka | RisingWave | - | 6 | 29 | 25 | - | - | 93 | - | PASS |
| P04 Redpanda + Flink + Iceberg | Redpanda | Flink | Iceberg | 9 | 21 | 24 | - | - | 147 | - | PASS |
| P05 Redpanda + Spark + Iceberg | Redpanda | Spark | Iceberg | 9 | 18 | 25 | - | - | 93 | - | PASS |
| P06 Redpanda + RisingWave | Redpanda | RisingWave | - | 6 | 28 | 25 | - | - | 93 | - | PASS |

### Kafka vs Redpanda (Broker Comparison)

Holding processing + storage constant, only the broker differs:

- **Flink+Iceberg**: Kafka 151s / -MB vs Redpanda 147s / -MB
- **Spark+Iceberg**: Kafka 93s / -MB vs Redpanda 93s / -MB
- **RisingWave**: Kafka 93s / -MB vs Redpanda 93s / -MB

### Flink vs Spark vs RisingWave (Processor Comparison)

Holding Kafka as broker, only the processor differs:

- **Flink** (P01): Total 151s, Memory -MB, Rate 24 evt/s
- **Spark** (P02): Total 93s, Memory -MB, Rate 26 evt/s
- **RisingWave** (P03): Total 93s, Memory -MB, Rate 25 evt/s

## Tier 2: Orchestration Comparison (Kestra / Airflow / Dagster)

Same Kafka+Flink+Iceberg data path, different orchestrators.

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P07 Kestra Orchestrated | 10 | 24 | 100 | - | PASS | Lightest orchestrator (+485 MB over P01) |
| P08 Airflow Orchestrated | 13 | 24 | 119 | - | PASS | Heaviest orchestrator (+1500 MB); Astro CLI not... |
| P09 Dagster Orchestrated | 11 | 24 | 97 | - | PASS | Mid-weight orchestrator; similar to Prefect |

## Tier 3: Serving Layer (ClickHouse)

P10 Serving Comparison: 6 services. ClickHouse + Metabase + Superset services healthy

See `pipelines/10-serving-comparison/benchmark_results/` for detailed query latencies.

## Tier 4: Observability (Elementary + Soda Core)

P11 Observability Stack: **awaiting benchmark** (status READY)

See `pipelines/11-observability-stack/observability_results/` for quality reports.

## Tier 5: CDC Pipelines (Debezium / Full Stack Capstone)

Change Data Capture pipelines: PostgreSQL WAL captured by Debezium and streamed through Kafka Connect.

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P12 CDC Debezium Pipeline | 10 | 0.3 | 139 | - | PASS | PostgreSQL WAL → Debezium → Kafka → Flink → Ice... |
| P23 Full Stack Capstone | 12 | 0.3 | 176 | - | PASS | PG → Debezium → Kafka → Flink → Iceberg → dbt →... |

## Tier 6: Alternative Table Formats (Delta Lake / Hudi)

Delta Lake (P13) and Apache Hudi (P22) compared against Iceberg in Tier 1 (P01, P02).

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P13 Kafka + Spark + Delta Lake | 8 | 2 | 112 | - | PASS | Fixed: delta_scan()→read_parquet glob; s3_endpo... |
| P22 Kafka + Spark + Hudi | 8 | 2 | 110 | - | PASS | Fixed: stg_yellow_trips uses Spark Silver snake... |

## Tier 7: Alternative Streaming SQL (Materialize)

Materialize (P14) as an alternative to RisingWave (P03). Both are PG-wire-compatible streaming SQL engines.

> **Pending benchmarks:** P14 Kafka + Materialize (status READY -- run benchmarks to include in comparison)

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P14 Kafka + Materialize | 6 | 25 | 63 | - | READY | Materialize dbt: schema doubling + CTE syntax i... |

## Tier 8: Lightweight Stream Processors (Kafka Streams / Bytewax)

Library-based processors with no separate cluster: Kafka Streams (P15, Java) and Bytewax (P20, Python).

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P15 Kafka Streams | 5 | 3 | 115 | - | PASS | Fixed: kafka-init service pre-creates topics; r... |
| P20 Kafka + Bytewax | 6 | 3 | 62 | - | PASS | Python-based stream processor; fastest ingestio... |

## Tier 9: OLAP Engines (Pinot / Druid)

Apache Pinot (P16) and Apache Druid (P17) as alternatives to ClickHouse (P10).

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P16 Redpanda + Flink + Pinot | 11 | 24 | 136 | - | PASS | Flink → Iceberg + Pinot serving |
| P17 Kafka + Flink + Druid | 14 | 24 | 101 | - | PASS | Flink → Iceberg + Druid serving |

## Tier 10: Additional Orchestrators (Prefect / Mage AI)

Prefect (P18) and Mage AI (P19) extend the orchestration comparison from Tier 2.

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P18 Prefect Orchestrated | 10 | 24 | 116 | - | PASS | Similar overhead to Dagster |
| P19 Mage AI | 6 | - | 51 | - | PASS | Interactive UI pipeline; services healthy |

## Tier 11: ML Feature Store (Feast)

Feast (P21) materialises Iceberg-based features into an online store for ML serving.

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P21 Feast Feature Store | 9 | 24 | 116 | - | PASS | Flink processes; Feast materialises features |

---

# Cross-Cutting Comparisons

## Table Format Comparison: Iceberg vs Delta Lake vs Hudi

All three use Kafka for ingestion and write to MinIO object storage. Iceberg and Hudi use different table formats on the same Parquet base. Delta Lake uses its own log-based protocol.

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Storage | Notes |
|----------|----------|-------------------|----------------------|-------------|---------|-------|
| Iceberg (P01 Kafka+Flink) (PASS) | 8 | 24 | 151 | - | Iceberg | Production reference pipeline; all audit i... |
| Delta Lake (P13 Kafka+Spark) (PASS) | 8 | 2 | 112 | - | Delta Lake | Fixed: delta_scan()→read_parquet glob; s3_... |
| Hudi (P22 Kafka+Spark) (PASS) | 8 | 2 | 110 | - | Hudi | Fixed: stg_yellow_trips uses Spark Silver ... |

- **Fastest processing**: Hudi (P22 Kafka+Spark) (110s)
- **Fewest services**: Iceberg (P01 Kafka+Flink) (8 services)
- **Highest ingestion rate**: Iceberg (P01 Kafka+Flink) (24 evt/s)

## OLAP Engine Comparison: ClickHouse vs Pinot vs Druid

All three serve analytical queries over taxi data. ClickHouse is column-oriented SQL, Pinot is real-time OLAP with Kafka ingestion, Druid is time-series optimised with Kafka supervisors.

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Storage | Notes |
|----------|----------|-------------------|----------------------|-------------|---------|-------|
| ClickHouse (P10) (PASS) | 6 | - | 35 | - | ClickHouse | ClickHouse + Metabase + Superset services ... |
| Apache Pinot (P16) (PASS) | 11 | 24 | 136 | - | Pinot | Flink → Iceberg + Pinot serving |
| Apache Druid (P17) (PASS) | 14 | 24 | 101 | - | Druid | Flink → Iceberg + Druid serving |

- **Fastest processing**: ClickHouse (P10) (35s)
- **Fewest services**: ClickHouse (P10) (6 services)
- **Highest ingestion rate**: Apache Pinot (P16) (24 evt/s)

## All Orchestrators: Kestra vs Airflow vs Dagster vs Prefect vs Mage

All wrap the same Kafka+Flink+Iceberg data path (except Mage which uses its own block-based processing). Comparison focuses on overhead: memory, container count, startup, and E2E time.

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Storage | Notes |
|----------|----------|-------------------|----------------------|-------------|---------|-------|
| Kestra (P07) (PASS) | 10 | 24 | 100 | - | Iceberg | Lightest orchestrator (+485 MB over P01) |
| Airflow (P08) (PASS) | 13 | 24 | 119 | - | Iceberg | Heaviest orchestrator (+1500 MB); Astro CL... |
| Dagster (P09) (PASS) | 11 | 24 | 97 | - | Iceberg | Mid-weight orchestrator; similar to Prefect |
| Prefect (P18) (PASS) | 10 | 24 | 116 | - | Iceberg | Similar overhead to Dagster |
| Mage AI (P19) (PASS) | 6 | - | 51 | - | - | Interactive UI pipeline; services healthy |

- **Fastest processing**: Mage AI (P19) (51s)
- **Fewest services**: Mage AI (P19) (6 services)
- **Highest ingestion rate**: Kestra (P07) (24 evt/s)

## Streaming SQL: RisingWave vs Materialize

Both are PostgreSQL-wire-compatible streaming SQL engines that maintain materialised views over Kafka topics. RisingWave is Rust-based; Materialize is built on Timely Dataflow.

> **Pending benchmarks:** P14 Kafka + Materialize (status READY -- run benchmarks to include in comparison)

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Storage | Notes |
|----------|----------|-------------------|----------------------|-------------|---------|-------|
| RisingWave (P03) (PASS) | 6 | 25 | 93 | - | - | Fixed: risingwave_view_override macro; DRO... |
| Materialize (P14) (READY) | 6 | 25 | 63 | - | - | Materialize dbt: schema doubling + CTE syn... |

## Lightweight Stream Processors: Kafka Streams vs Bytewax

Both are library-based processors that run inside the application JVM/Python process -- no separate cluster. Kafka Streams requires the JVM; Bytewax is pure Python.

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Storage | Notes |
|----------|----------|-------------------|----------------------|-------------|---------|-------|
| Kafka Streams (P15, Java) (PASS) | 5 | 3 | 115 | - | - | Fixed: kafka-init service pre-creates topi... |
| Bytewax (P20, Python) (PASS) | 6 | 3 | 62 | - | - | Python-based stream processor; fastest ing... |

- **Fastest processing**: Bytewax (P20, Python) (62s)
- **Fewest services**: Kafka Streams (P15, Java) (5 services)
- **Highest ingestion rate**: Kafka Streams (P15, Java) (3 evt/s)

## CDC Comparison: Debezium Standalone vs Full Stack Capstone

P12 is standalone Debezium CDC (PostgreSQL WAL -> Kafka Connect -> Flink -> Iceberg). P23 extends it into a full stack capstone adding ClickHouse serving and Grafana dashboards.

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Storage | Notes |
|----------|----------|-------------------|----------------------|-------------|---------|-------|
| Debezium CDC (P12) (PASS) | 10 | 0.3 | 139 | - | Iceberg | PostgreSQL WAL → Debezium → Kafka → Flink ... |
| Full Stack Capstone (P23) (PASS) | 12 | 0.3 | 176 | - | Iceberg | PG → Debezium → Kafka → Flink → Iceberg → ... |

- **Fastest processing**: Debezium CDC (P12) (139s)
- **Fewest services**: Debezium CDC (P12) (10 services)
- **Highest ingestion rate**: Debezium CDC (P12) (0.3 evt/s)

---

# Overall Recommendations

- **Fastest E2E processing**: P10 Serving Comparison (35s)
- **Simplest (fewest services)**: P00 Batch Baseline (dbt only) (4 services)
- **Highest ingestion rate**: P02 Kafka + Spark + Iceberg (26 evt/s)

### Benchmark Coverage

- **Benchmarked**: 22/24 pipelines (91%)
- **Pending**: 2 pipelines awaiting benchmarks:
  - P11 Observability Stack (Flink, Iceberg)
  - P14 Kafka + Materialize (Materialize, -)

# Pipeline Comparison Report

Auto-generated from benchmark results (24 pipelines in results.csv).

**Status**: 0 benchmarked (PASS), 24 pending (READY)

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

> **Pending benchmarks:** P00 batch-baseline, P01 Kafka + Flink + Iceberg, P02 kafka-spark-iceberg, P03 Kafka + RisingWave, P04 Redpanda + Flink + Iceberg, P05 redpanda-spark-iceberg, P06 Redpanda + RisingWave (status READY -- run benchmarks to include in comparison)

| Pipeline | Ingestion | Processing | Storage | Services | Startup (s) | Ingestion (evt/s) | Bronze (s) | Silver (s) | Total Processing (s) | Memory (MB) | Status |
|----------|-----------|------------|---------|----------|-------------|-------------------|------------|------------|----------------------|-------------|--------|
| P00 batch-baseline | - | - | - | - | - | - | - | - | - | - | READY |
| P01 Kafka + Flink + Iceberg | - | - | - | - | 14.14 | - | - | - | - | - | READY |
| P02 kafka-spark-iceberg | - | - | - | - | 18 | - | - | - | - | - | READY |
| P03 Kafka + RisingWave | - | - | - | - | 26.25 | - | - | - | - | - | READY |
| P04 Redpanda + Flink + Iceberg | - | - | - | - | 13.57 | - | - | - | - | - | READY |
| P05 redpanda-spark-iceberg | - | - | - | - | 19 | - | - | - | - | - | READY |
| P06 Redpanda + RisingWave | - | - | - | - | 22.17 | - | - | - | - | - | READY |

### Kafka vs Redpanda (Broker Comparison)

Holding processing + storage constant, only the broker differs:

- **Flink+Iceberg**: awaiting benchmarks for P01, P04
- **Spark+Iceberg**: awaiting benchmarks for P02, P05
- **RisingWave**: awaiting benchmarks for P03, P06

### Flink vs Spark vs RisingWave (Processor Comparison)

Holding Kafka as broker, only the processor differs:

- **Flink** (P01): awaiting benchmark
- **Spark** (P02): awaiting benchmark
- **RisingWave** (P03): awaiting benchmark

## Tier 2: Orchestration Comparison (Kestra / Airflow / Dagster)

Same Kafka+Flink+Iceberg data path, different orchestrators.

> **Pending benchmarks:** P07 Kestra Orchestrated, P08 airflow-orchestrated, P09 dagster-orchestrated (status READY -- run benchmarks to include in comparison)

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P07 Kestra Orchestrated | - | - | - | - | READY |  |
| P08 airflow-orchestrated | - | - | - | - | READY |  |
| P09 dagster-orchestrated | - | - | - | - | READY |  |

## Tier 3: Serving Layer (ClickHouse)

P10 serving-comparison: **awaiting benchmark** (status READY)

See `pipelines/10-serving-comparison/benchmark_results/` for detailed query latencies.

## Tier 4: Observability (Elementary + Soda Core)

P11 observability-stack: **awaiting benchmark** (status READY)

See `pipelines/11-observability-stack/observability_results/` for quality reports.

## Tier 5: CDC Pipelines (Debezium / Full Stack Capstone)

Change Data Capture pipelines: PostgreSQL WAL captured by Debezium and streamed through Kafka Connect.

> **Pending benchmarks:** P12 CDC Debezium Pipeline, P23 full-stack-capstone (status READY -- run benchmarks to include in comparison)

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P12 CDC Debezium Pipeline | - | - | - | - | READY |  |
| P23 full-stack-capstone | - | - | - | - | READY |  |

## Tier 6: Alternative Table Formats (Delta Lake / Hudi)

Delta Lake (P13) and Apache Hudi (P22) compared against Iceberg in Tier 1 (P01, P02).

> **Pending benchmarks:** P13 Kafka + Spark + Delta Lake, P22 Hudi CDC Storage (status READY -- run benchmarks to include in comparison)

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P13 Kafka + Spark + Delta Lake | - | - | - | - | READY |  |
| P22 Hudi CDC Storage | - | - | - | - | READY |  |

## Tier 7: Alternative Streaming SQL (Materialize)

Materialize (P14) as an alternative to RisingWave (P03). Both are PG-wire-compatible streaming SQL engines.

> **Pending benchmarks:** P14 Kafka + Materialize (status READY -- run benchmarks to include in comparison)

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P14 Kafka + Materialize | - | - | - | - | READY |  |

## Tier 8: Lightweight Stream Processors (Kafka Streams / Bytewax)

Library-based processors with no separate cluster: Kafka Streams (P15, Java) and Bytewax (P20, Python).

> **Pending benchmarks:** P15 Kafka Streams, P20 kafka-bytewax (status READY -- run benchmarks to include in comparison)

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P15 Kafka Streams | - | - | - | - | READY |  |
| P20 kafka-bytewax | - | - | - | - | READY |  |

## Tier 9: OLAP Engines (Pinot / Druid)

Apache Pinot (P16) and Apache Druid (P17) as alternatives to ClickHouse (P10).

> **Pending benchmarks:** P16 pinot-serving, P17 druid-timeseries (status READY -- run benchmarks to include in comparison)

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P16 pinot-serving | - | - | - | - | READY |  |
| P17 druid-timeseries | - | - | - | - | READY |  |

## Tier 10: Additional Orchestrators (Prefect / Mage AI)

Prefect (P18) and Mage AI (P19) extend the orchestration comparison from Tier 2.

> **Pending benchmarks:** P18 prefect-orchestrated, P19 Mage AI (status READY -- run benchmarks to include in comparison)

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P18 prefect-orchestrated | - | - | - | - | READY |  |
| P19 Mage AI | - | - | - | - | READY |  |

## Tier 11: ML Feature Store (Feast)

Feast (P21) materialises Iceberg-based features into an online store for ML serving.

> **Pending benchmarks:** P21 Feast Feature Store (status READY -- run benchmarks to include in comparison)

| Pipeline | Services | Ingestion (evt/s) | Total Processing (s) | Memory (MB) | Status | Notes |
|----------|----------|-------------------|----------------------|-------------|--------|-------|
| P21 Feast Feature Store | - | - | - | - | READY |  |

---

# Cross-Cutting Comparisons

## Table Format Comparison: Iceberg vs Delta Lake vs Hudi

All three use Kafka for ingestion and write to MinIO object storage. Iceberg and Hudi use different table formats on the same Parquet base. Delta Lake uses its own log-based protocol.

> **Pending benchmarks:** P01 Kafka + Flink + Iceberg, P13 Kafka + Spark + Delta Lake, P22 Hudi CDC Storage (status READY -- run benchmarks to include in comparison)

*No benchmarked pipelines in this comparison yet. Run benchmarks to populate.*

## OLAP Engine Comparison: ClickHouse vs Pinot vs Druid

All three serve analytical queries over taxi data. ClickHouse is column-oriented SQL, Pinot is real-time OLAP with Kafka ingestion, Druid is time-series optimised with Kafka supervisors.

> **Pending benchmarks:** P10 serving-comparison, P16 pinot-serving, P17 druid-timeseries (status READY -- run benchmarks to include in comparison)

*No benchmarked pipelines in this comparison yet. Run benchmarks to populate.*

## All Orchestrators: Kestra vs Airflow vs Dagster vs Prefect vs Mage

All wrap the same Kafka+Flink+Iceberg data path (except Mage which uses its own block-based processing). Comparison focuses on overhead: memory, container count, startup, and E2E time.

> **Pending benchmarks:** P07 Kestra Orchestrated, P08 airflow-orchestrated, P09 dagster-orchestrated, P18 prefect-orchestrated, P19 Mage AI (status READY -- run benchmarks to include in comparison)

*No benchmarked pipelines in this comparison yet. Run benchmarks to populate.*

## Streaming SQL: RisingWave vs Materialize

Both are PostgreSQL-wire-compatible streaming SQL engines that maintain materialised views over Kafka topics. RisingWave is Rust-based; Materialize is built on Timely Dataflow.

> **Pending benchmarks:** P03 Kafka + RisingWave, P14 Kafka + Materialize (status READY -- run benchmarks to include in comparison)

*No benchmarked pipelines in this comparison yet. Run benchmarks to populate.*

## Lightweight Stream Processors: Kafka Streams vs Bytewax

Both are library-based processors that run inside the application JVM/Python process -- no separate cluster. Kafka Streams requires the JVM; Bytewax is pure Python.

> **Pending benchmarks:** P15 Kafka Streams, P20 kafka-bytewax (status READY -- run benchmarks to include in comparison)

*No benchmarked pipelines in this comparison yet. Run benchmarks to populate.*

## CDC Comparison: Debezium Standalone vs Full Stack Capstone

P12 is standalone Debezium CDC (PostgreSQL WAL -> Kafka Connect -> Flink -> Iceberg). P23 extends it into a full stack capstone adding ClickHouse serving and Grafana dashboards.

> **Pending benchmarks:** P12 CDC Debezium Pipeline, P23 full-stack-capstone (status READY -- run benchmarks to include in comparison)

*No benchmarked pipelines in this comparison yet. Run benchmarks to populate.*

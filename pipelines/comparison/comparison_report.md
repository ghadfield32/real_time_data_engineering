# Pipeline Comparison Report

> Comprehensive benchmark analysis of 12 pipelines processing NYC Yellow Taxi data (January 2024, ~2.96M rows source, 10K events per streaming test run). All measurements taken on the same host, February 2026.

---

## 1. Executive Summary

This report compares 12 data engineering pipelines spanning batch processing, real-time streaming, orchestration, serving, and observability. Each pipeline was built on the NYC Yellow Taxi dataset and verified end-to-end through the Medallion architecture (Bronze, Silver, Gold).

### Key Findings

| Category | Winner | Details |
|----------|--------|---------|
| **Fastest Processing** | Pipeline 03/06 (RisingWave) | ~2s total -- materialized views process events as they arrive |
| **Highest Ingestion Rate** | Pipeline 04 (Redpanda+Flink) | 25,139 events/sec |
| **Lowest Memory** | Pipeline 06 (Redpanda+RisingWave) | 449 MB total -- lightest streaming pipeline |
| **Fewest Services** | Pipeline 00 (Batch Baseline) | 1 service; Pipeline 06 is lightest streaming at 3 |
| **Best Batch Throughput** | Pipeline 00 (dbt+DuckDB) | 2,964,624 rows in 9.19s (322K rows/sec) |
| **Fastest Startup** | Pipeline 02 (Kafka+Spark) | 18s to healthy |
| **Best dbt Integration** | Pipeline 09 (Dagster) | Native asset-per-model lineage |
| **Simplest Streaming Setup** | Pipeline 06 (Redpanda+RisingWave) | 3 services, pure SQL, no JVM, no object storage |
| **Best Query Performance** | Pipeline 10 (ClickHouse) | Sub-50ms on 2.76M rows for all analytical queries |

### When to Use What

- **You just need analytics on static data**: Pipeline 00 (Batch). Nothing beats dbt+DuckDB for simplicity and raw throughput on files.
- **You need real-time with minimal infrastructure**: Pipeline 06 (Redpanda+RisingWave). Three services, 449 MB, SQL-only.
- **You need the Iceberg open table format**: Pipeline 04 (Redpanda+Flink) for best ingestion rate, or Pipeline 02 (Kafka+Spark) for lowest memory among Iceberg pipelines.
- **You need orchestration**: Pipeline 09 (Dagster) for dbt-heavy work, Pipeline 07 (Kestra) for simplest setup, Pipeline 08 (Airflow) for largest ecosystem.
- **You need sub-second analytical queries**: Pipeline 10 (ClickHouse + Metabase/Superset).

---

## 2. Benchmark Results Table

### Streaming Pipelines (10,000 events per test)

| # | Pipeline | Services | Startup (s) | Ingestion (evt/s) | Bronze (s) | Silver (s) | Total Processing (s) | Memory (MB) | Bronze Rows | Silver Rows |
|---|----------|:--------:|:-----------:|:-----------------:|:----------:|:----------:|:--------------------:|:-----------:|:-----------:|:-----------:|
| 01 | Kafka+Flink+Iceberg | 7 | 31 | 18,586 | 13 | 9 | 24 | 2,870 | 10,000 | 9,855 |
| 02 | Kafka+Spark+Iceberg | 6 | 18 | 24,370 | 12 | 10 | 24 | 1,230 | 10,000 | 9,739 |
| 03 | Kafka+RisingWave | 4 | 34 | 18,069 | auto | auto | ~2 | 687 | 10,000 | 9,766 |
| 04 | Redpanda+Flink+Iceberg | 6 | 26 | 25,139 | 14 | 11 | 27 | 1,860 | 10,000 | 9,855 |
| 05 | Redpanda+Spark+Iceberg | 5 | 19 | 24,636 | 16 | 12 | 30 | 917 | 10,000 | 9,739 |
| 06 | Redpanda+RisingWave | 3 | 34 | 18,030 | auto | auto | ~2 | 449 | 10,000 | 9,766 |

### Orchestrated Pipelines (base: Kafka+Flink+Iceberg)

| # | Pipeline | Services | Startup (s) | Ingestion (evt/s) | Bronze (s) | Silver (s) | Total Processing (s) | Memory (MB) |
|---|----------|:--------:|:-----------:|:-----------------:|:----------:|:----------:|:--------------------:|:-----------:|
| 07 | Kestra Orchestrated | 9 | 31 | 22,534 | 14 | 10 | 26 | 2,890 |
| 08 | Airflow Orchestrated | 7+ | 31 | 20,558 | 14 | 11 | 27 | 2,230 (+1,500 Astro) |
| 09 | Dagster Orchestrated | 10 | 31 | 23,310 | 13 | 11 | 26 | 2,770 |

### Batch and Specialty Pipelines

| # | Pipeline | Services | Total Time | Rows Processed | Memory | Key Metric |
|---|----------|:--------:|:----------:|:--------------:|:------:|:----------:|
| 00 | Batch Baseline | 1 | 21s (9.19s build) | 2,964,624 | Minimal | 91/91 dbt tests pass |
| 10 | Serving Comparison | 4 | N/A | 2,760,000 | N/A | All queries <50ms |
| 11 | Observability Stack | 8 | Same as P01 | 10,000 | ~P01 | Elementary + Soda Core |

---

## 3. Speed Rankings

### By Total Processing Time (lower is better)

| Rank | Pipeline | Total Processing | Notes |
|:----:|----------|:----------------:|-------|
| 1 | P03 Kafka+RisingWave | **~2s** | Materialized views -- continuous processing |
| 1 | P06 Redpanda+RisingWave | **~2s** | Materialized views -- continuous processing |
| 3 | P01 Kafka+Flink+Iceberg | **24s** | Batch-mode Flink SQL jobs |
| 3 | P02 Kafka+Spark+Iceberg | **24s** | PySpark Structured Streaming |
| 5 | P07 Kestra Orchestrated | **26s** | +2s orchestration overhead vs P01 |
| 5 | P09 Dagster Orchestrated | **26s** | +2s orchestration overhead vs P01 |
| 7 | P04 Redpanda+Flink+Iceberg | **27s** | Slightly slower Flink processing than P01 |
| 7 | P08 Airflow Orchestrated | **27s** | +3s orchestration overhead vs P01 |
| 9 | P05 Redpanda+Spark+Iceberg | **30s** | Slowest of the Iceberg pipelines |

### By Ingestion Rate (higher is better)

| Rank | Pipeline | Ingestion Rate | Broker |
|:----:|----------|:--------------:|--------|
| 1 | P04 Redpanda+Flink+Iceberg | **25,139 evt/s** | Redpanda |
| 2 | P05 Redpanda+Spark+Iceberg | **24,636 evt/s** | Redpanda |
| 3 | P02 Kafka+Spark+Iceberg | **24,370 evt/s** | Kafka |
| 4 | P09 Dagster Orchestrated | **23,310 evt/s** | Kafka |
| 5 | P07 Kestra Orchestrated | **22,534 evt/s** | Kafka |
| 6 | P08 Airflow Orchestrated | **20,558 evt/s** | Kafka |
| 7 | P01 Kafka+Flink+Iceberg | **18,586 evt/s** | Kafka |
| 8 | P03 Kafka+RisingWave | **18,069 evt/s** | Kafka |
| 9 | P06 Redpanda+RisingWave | **18,030 evt/s** | Redpanda |

### By Startup Time (lower is better)

| Rank | Pipeline | Startup | Bottleneck |
|:----:|----------|:-------:|------------|
| 1 | P02 Kafka+Spark+Iceberg | **18s** | Spark worker registration |
| 2 | P05 Redpanda+Spark+Iceberg | **19s** | Spark worker registration |
| 3 | P04 Redpanda+Flink+Iceberg | **26s** | Flink TaskManager |
| 4 | P01 Kafka+Flink+Iceberg | **31s** | Schema Registry + Flink |
| 4 | P07 Kestra Orchestrated | **31s** | Same as P01 + Kestra |
| 4 | P08 Airflow Orchestrated | **31s** | Same as P01 (Astro separate) |
| 4 | P09 Dagster Orchestrated | **31s** | Same as P01 + Dagster |
| 8 | P03 Kafka+RisingWave | **34s** | RisingWave initialization |
| 8 | P06 Redpanda+RisingWave | **34s** | RisingWave initialization |

---

## 4. Broker Comparison: Kafka vs Redpanda

Each broker was tested with three different processors to isolate the broker variable. All pairs use identical processing logic and produce identical results.

### Paired Comparisons

#### Pair 1: Flink+Iceberg (P01 vs P04)

| Metric | P01 (Kafka) | P04 (Redpanda) | Delta |
|--------|:-----------:|:--------------:|:-----:|
| Services | 7 | 6 | Redpanda -1 (no Schema Registry) |
| Startup | 31s | 26s | **Redpanda 5s faster** |
| Ingestion | 18,586 evt/s | 25,139 evt/s | **Redpanda +35% faster** |
| Total Processing | 24s | 27s | Kafka 3s faster |
| Memory | 2,870 MB | 1,860 MB | **Redpanda -1,010 MB (35% less)** |
| Silver Rows | 9,855 | 9,855 | Identical |

#### Pair 2: Spark+Iceberg (P02 vs P05)

| Metric | P02 (Kafka) | P05 (Redpanda) | Delta |
|--------|:-----------:|:--------------:|:-----:|
| Services | 6 | 5 | Redpanda -1 |
| Startup | 18s | 19s | Comparable |
| Ingestion | 24,370 evt/s | 24,636 evt/s | Comparable (+1%) |
| Total Processing | 24s | 30s | Kafka 6s faster |
| Memory | 1,230 MB | 917 MB | **Redpanda -313 MB (25% less)** |
| Silver Rows | 9,739 | 9,739 | Identical |

#### Pair 3: RisingWave (P03 vs P06)

| Metric | P03 (Kafka) | P06 (Redpanda) | Delta |
|--------|:-----------:|:--------------:|:-----:|
| Services | 4 | 3 | Redpanda -1 |
| Startup | 34s | 34s | Identical |
| Ingestion | 18,069 evt/s | 18,030 evt/s | Comparable |
| Total Processing | ~2s | ~2s | Identical |
| Memory | 687 MB | 449 MB | **Redpanda -238 MB (35% less)** |
| Silver Rows | 9,766 | 9,766 | Identical |

### Broker Summary

| Aspect | Kafka (KRaft) | Redpanda |
|--------|:-------------:|:--------:|
| Containers needed | 2 (Kafka + Schema Registry) | 1 (built-in registry) |
| Average memory savings | -- | **35% less per pair** |
| Average ingestion rate | 20,342 evt/s | 22,602 evt/s |
| JVM dependency | Yes | No (C++/Go) |
| Wire protocol | Native | Kafka-compatible |
| Community/ecosystem | Largest; industry standard | Growing; simpler ops |
| Setup complexity | Medium (KRaft config) | Low (CLI flags) |
| Healthcheck | `kafka-broker-api-versions.sh` | `rpk cluster health` |

**Verdict**: Redpanda consistently uses less memory (35% average savings) and requires one fewer container. Ingestion rates are comparable to slightly better. Kafka offers the larger ecosystem and native protocol. For new projects optimizing for operational simplicity, Redpanda is the pragmatic choice. For environments already invested in the Kafka ecosystem, there is no compelling performance reason to switch.

---

## 5. Processor Comparison: Flink vs Spark vs RisingWave

Using Kafka-based pipelines (P01 vs P02 vs P03) to isolate the processor variable.

### Head-to-Head

| Metric | P01 (Flink SQL) | P02 (Spark) | P03 (RisingWave) |
|--------|:---------------:|:-----------:|:-----------------:|
| Services | 7 | 6 | 4 |
| Startup | 31s | 18s | 34s |
| Ingestion Rate | 18,586 evt/s | 24,370 evt/s | 18,069 evt/s |
| Bronze Processing | 13s | 12s | auto |
| Silver Processing | 9s | 10s | auto |
| Total Processing | 24s | 24s | **~2s** |
| Memory | 2,870 MB | 1,230 MB | **687 MB** |
| Silver Rows | 9,855 | 9,739 | 9,766 |
| Processing Model | Micro-batch (bounded) | Micro-batch (availableNow) | **Continuous (MVs)** |
| Language | SQL | PySpark (Python) | SQL |
| JVM Required | Yes | Yes | **No (Rust)** |
| Custom Dockerfile | Yes (7 JARs) | Yes (6 JARs) | **No (stock image)** |
| Storage Format | Iceberg on MinIO (S3) | Iceberg on MinIO (S3) | Internal (PG-compatible) |
| dbt Adapter | dbt-duckdb (iceberg_scan) | dbt-duckdb (iceberg_scan) | dbt-postgres (native) |
| Custom Code | 0 lines (pure SQL) | ~300 lines Python | 0 lines (pure SQL) |

### Processing Time Breakdown (10,000 events)

```
Flink (P01):      |===Bronze 13s===|==Silver 9s==|  Total: 24s
Spark (P02):      |==Bronze 12s==|==Silver 10s===|  Total: 24s
RisingWave (P03): |MV~2s|                           Total: ~2s
                  0s        10s        20s        30s
```

### Processor Verdicts

**Flink SQL**: Best for teams that want pure SQL with Iceberg output and are comfortable with JVM infrastructure. Strong for complex event processing (CEP), windowed aggregations, and exactly-once semantics. Highest memory cost.

**Spark Structured Streaming**: Best for teams with existing PySpark expertise. Fastest startup (18s). Moderate memory (1,230 MB). Offers the richest API for complex transformations beyond SQL. Requires managing Python code and JAR dependencies.

**RisingWave**: Best for lowest latency and simplest setup. Materialized views deliver ~2s end-to-end (12x faster than batch processors). Lowest memory (687 MB) and fewest services (4). Trade-off: data lives in RisingWave's internal storage, not in an open table format like Iceberg.

---

## 6. Orchestrator Comparison: Kestra vs Airflow vs Dagster

All three orchestrators wrap the same base pipeline (Kafka+Flink+Iceberg, Pipeline 01) to isolate the orchestration overhead.

### Overhead Analysis

| Metric | P01 (Base) | P07 (Kestra) | P08 (Airflow) | P09 (Dagster) |
|--------|:----------:|:------------:|:-------------:|:-------------:|
| Services | 7 | 9 (+2) | 7 + Astro (+~4) | 10 (+3) |
| Startup | 31s | 31s | 31s + Astro | 31s |
| Ingestion | 18,586 evt/s | 22,534 evt/s | 20,558 evt/s | 23,310 evt/s |
| Total Processing | 24s | 26s (+2s) | 27s (+3s) | 26s (+2s) |
| Memory (infra) | 2,870 MB | 2,890 MB (+20 MB) | 2,230 MB (+~1,500 Astro) | 2,770 MB (-100 MB) |
| Added Memory | -- | +485 MB (Kestra+PG) | +~1,500 MB (Astronomer) | +502 MB (Dagster+PG) |
| UI Port | -- | :8083 | :8080 | :3000 |

### Orchestration Overhead Summary

| Orchestrator | Processing Overhead | Memory Overhead | Setup Complexity |
|--------------|:-------------------:|:---------------:|:----------------:|
| Kestra | +2s (8%) | +485 MB | Lowest -- single container, YAML config |
| Airflow (Astronomer) | +3s (12%) | +~1,500 MB | Highest -- `astro dev start`, separate lifecycle |
| Dagster | +2s (8%) | +502 MB | Medium -- 3 containers, Python config |

### Feature Comparison

| Feature | Kestra | Airflow | Dagster |
|---------|:------:|:-------:|:-------:|
| Config language | YAML | Python | Python |
| Scheduling | Cron + event triggers | Cron + sensors | Cron + sensors + freshness |
| dbt integration | CLI plugin (BashOperator) | BashOperator / Cosmos | dagster-dbt (asset-based) |
| Per-model visibility | No (single task) | Yes (with Cosmos) | **Yes (each model = asset)** |
| Lineage tracking | Flow-level | DAG-level | **Asset graph** |
| Web editor | **Yes (built-in)** | No | No |
| Learning curve | Low | Medium | Medium |
| Community size | Growing | **Very large (most mature)** | Large (fastest growing) |
| Plugin ecosystem | Moderate | **Extensive** | Moderate |
| Production maturity | Emerging | **Battle-tested** | Production-ready |
| Hot-reload | No | No | **Yes** |

### Orchestrator Verdicts

**Kestra (P07)**: Lowest barrier to entry. Single container, YAML-first configuration, built-in web editor. Ideal for teams that want orchestration without writing Python. Smallest memory overhead (+485 MB). Best for: small teams, YAML-first workflows, event-driven pipelines.

**Airflow via Astronomer (P08)**: The industry standard. Largest ecosystem of operators and hooks. Cosmos integration provides per-model dbt visibility. Highest memory overhead (+~1,500 MB) due to Astronomer's multi-container architecture. Best for: enterprise teams, existing Airflow shops, complex multi-system DAGs.

**Dagster (P09)**: Best-in-class dbt integration via `dagster-dbt`. Each dbt model becomes a trackable asset with lineage. Hot-reload development experience. Moderate overhead (+502 MB). Best for: dbt-heavy workloads, teams that value data lineage, asset-centric thinking.

---

## 7. Memory Efficiency Rankings

### Streaming Pipelines (lower is better)

| Rank | Pipeline | Total Memory | Breakdown |
|:----:|----------|:------------:|-----------|
| 1 | **P06 Redpanda+RisingWave** | **449 MB** | RisingWave 218 MB, Redpanda 232 MB |
| 2 | P03 Kafka+RisingWave | 687 MB | RisingWave 319 MB, Kafka 368 MB |
| 3 | P05 Redpanda+Spark+Iceberg | 917 MB | Spark Master 318 MB, Worker 299 MB, Redpanda 193 MB, MinIO 108 MB |
| 4 | P02 Kafka+Spark+Iceberg | 1,230 MB | Spark Master 513 MB, Worker 298 MB, MinIO 106 MB, Kafka 315 MB |
| 5 | P04 Redpanda+Flink+Iceberg | 1,860 MB | Flink TM 875 MB, JM 641 MB, MinIO 106 MB, Redpanda 237 MB |
| 6 | P08 Airflow Orchestrated | 2,230 MB* | Infra only; +~1,500 MB for Astronomer containers |
| 7 | P09 Dagster Orchestrated | 2,770 MB | P01 base + Dagster webserver/daemon + Postgres |
| 8 | P01 Kafka+Flink+Iceberg | 2,870 MB | Flink TM 930 MB, JM 886 MB, SR 428 MB, Kafka 492 MB, MinIO 133 MB |
| 9 | P07 Kestra Orchestrated | 2,890 MB | P01 base + Kestra + embedded DB |

*P08 Airflow is 2,230 MB for infrastructure only; Astronomer adds approximately 1,500 MB, bringing the effective total to ~3,730 MB.

### Memory per Service

| Pipeline | Memory (MB) | Services | MB/Service |
|----------|:-----------:|:--------:|:----------:|
| P06 Redpanda+RisingWave | 449 | 3 | **150** |
| P03 Kafka+RisingWave | 687 | 4 | 172 |
| P05 Redpanda+Spark | 917 | 5 | 183 |
| P02 Kafka+Spark | 1,230 | 6 | 205 |
| P04 Redpanda+Flink | 1,860 | 6 | 310 |
| P09 Dagster | 2,770 | 10 | 277 |
| P07 Kestra | 2,890 | 9 | 321 |
| P01 Kafka+Flink | 2,870 | 7 | 410 |
| P08 Airflow | 3,730 | 7+ | ~533 |

### What Drives Memory Usage

| Component | Typical Memory | Notes |
|-----------|:--------------:|-------|
| Flink TaskManager | 875-930 MB | JVM heap; largest single consumer |
| Flink JobManager | 641-886 MB | JVM heap; coordination overhead |
| Spark Master | 318-513 MB | JVM heap |
| Spark Worker | 298-299 MB | JVM heap; consistent across brokers |
| Kafka (KRaft) | 315-492 MB | JVM heap |
| Schema Registry | 428 MB | JVM heap; required only for Kafka |
| Redpanda | 193-237 MB | C++; no JVM overhead |
| RisingWave | 218-319 MB | Rust; efficient memory management |
| MinIO | 106-133 MB | Go; lightweight object storage |
| Kestra | ~485 MB | Java; includes embedded DB |
| Dagster (all) | ~502 MB | Python; webserver + daemon + Postgres |
| Astronomer Airflow | ~1,500 MB | Multiple containers (webserver, scheduler, triggerer, DB) |

---

## 8. Strengths and Weaknesses

### Brokers

#### Kafka (KRaft)

| Strengths | Weaknesses |
|-----------|------------|
| Industry standard; largest ecosystem | Requires JVM (higher memory) |
| Native protocol (all tools built for Kafka) | Needs separate Schema Registry container |
| Massive community, extensive documentation | More complex configuration (KRaft mode) |
| Proven at extreme scale (millions of events/sec) | 2 containers minimum (broker + SR) |
| Confluent ecosystem (connectors, ksqlDB) | Healthcheck requires Kafka CLI tools |

#### Redpanda

| Strengths | Weaknesses |
|-----------|------------|
| Single container (built-in Schema Registry) | Smaller community and ecosystem |
| 35% less memory than Kafka on average | Kafka-compatible but not Kafka-native |
| No JVM -- C++/Go binary | Fewer managed service options |
| Simpler configuration (CLI flags) | Less battle-tested at extreme scale |
| `rpk` CLI for easy management | Some edge-case protocol differences |

### Processors

#### Flink SQL

| Strengths | Weaknesses |
|-----------|------------|
| Pure SQL -- no custom code needed | Highest memory (1,800-2,870 MB with broker) |
| Industry standard for stream processing | 7 JARs to manage (Kafka, Iceberg, Hadoop, AWS) |
| Complex event processing (CEP) support | Custom Dockerfile required |
| Exactly-once semantics | Slowest startup when paired with Kafka (31s) |
| Rich windowing and temporal operations | Steeper learning curve for catalog configuration |

#### Spark Structured Streaming

| Strengths | Weaknesses |
|-----------|------------|
| Rich PySpark API for complex transforms | ~300 lines of Python code to manage |
| Fastest startup (18-19s) | 6 JARs to manage |
| Moderate memory (917-1,230 MB) | Custom Dockerfile required |
| Huge community, extensive documentation | Micro-batch latency (not true streaming) |
| Unified batch + streaming API | JAR version conflicts can be painful |

#### RisingWave

| Strengths | Weaknesses |
|-----------|------------|
| Lowest latency (~2s vs 24-30s) | Data in internal storage (not Iceberg) |
| Lowest memory (449-687 MB) | Smaller community (newer project) |
| Fewest services (3-4) | Less mature ecosystem |
| No JVM, no JARs, no custom Dockerfile | Limited to SQL (no Python API) |
| PostgreSQL-compatible (familiar SQL) | Fewer connectors than Flink/Spark |
| Materialized views -- true continuous processing | Less control over processing timing |

### Orchestrators

#### Kestra

| Strengths | Weaknesses |
|-----------|------------|
| YAML-first -- no Python required | Smallest plugin ecosystem |
| Built-in web flow editor | No per-model dbt visibility |
| Single container deployment | Emerging -- less production track record |
| Lowest memory overhead (+485 MB) | Smaller community |
| Event-driven architecture | Limited dbt integration depth |

#### Airflow (Astronomer)

| Strengths | Weaknesses |
|-----------|------------|
| Largest ecosystem of operators/hooks | Highest memory overhead (+~1,500 MB) |
| Battle-tested at scale | Complex multi-container architecture |
| Cosmos for dbt per-model visibility | Separate `astro dev start` lifecycle |
| Extensive documentation and community | Steeper learning curve |
| Most third-party integrations | DAG-centric (not asset-centric) |

#### Dagster

| Strengths | Weaknesses |
|-----------|------------|
| Best native dbt integration (dagster-dbt) | 3 additional containers required |
| Per-model asset lineage tracking | Moderate learning curve (asset model) |
| Hot-reload development experience | +502 MB memory overhead |
| Software-defined assets paradigm | Smaller plugin ecosystem than Airflow |
| Built-in data quality/freshness checks | Newer -- less production track record than Airflow |

---

## 9. When to Use Each Pipeline

### Decision by Team Profile

| Team Profile | Recommended Pipeline | Rationale |
|-------------|---------------------|-----------|
| **Small team, limited ops capacity** | P06 (Redpanda+RisingWave) | 3 services, 449 MB, pure SQL, minimal moving parts |
| **Data engineering team with PySpark skills** | P02 (Kafka+Spark+Iceberg) | Familiar APIs, good memory efficiency, Iceberg output |
| **Platform team building for the org** | P01 (Kafka+Flink+Iceberg) | Industry standard, SQL-based, Iceberg for interoperability |
| **Startup iterating quickly** | P03 (Kafka+RisingWave) | Fastest processing, PostgreSQL-compatible, iterate with SQL |
| **Enterprise with existing Kafka** | P04 (Redpanda+Flink) or stay with Kafka | Redpanda saves memory; Kafka if already invested |
| **Analytics/BI-focused team** | P00 (Batch) + P10 (ClickHouse) | dbt for transforms, ClickHouse for sub-50ms queries |
| **dbt-centric organization** | P09 (Dagster) | Asset-per-model lineage, native dbt integration |
| **Ops team wanting simple orchestration** | P07 (Kestra) | YAML config, web editor, single container |
| **Enterprise with Airflow in place** | P08 (Airflow/Astronomer) | Extend existing investment, Cosmos for dbt |
| **Compliance-heavy environment** | P11 (Observability) | Elementary + Soda Core for automated quality checks |

### Decision by Requirement

| Requirement | Best Choice | Why |
|-------------|-------------|-----|
| Lowest latency | P03/P06 (RisingWave) | ~2s with materialized views |
| Lowest memory footprint | P06 (Redpanda+RisingWave) | 449 MB total |
| Open table format (Iceberg) | P04 (Redpanda+Flink) | Best ingestion rate + Iceberg output |
| Highest ingestion throughput | P04 (Redpanda+Flink) | 25,139 events/sec |
| Fastest startup | P02 (Kafka+Spark) | 18s to healthy |
| Fewest containers | P06 (Redpanda+RisingWave) | 3 services |
| Full batch processing | P00 (Batch Baseline) | 2.96M rows in 9.19s, 91/91 tests |
| Sub-second OLAP queries | P10 (ClickHouse) | <50ms on 2.76M rows |
| dbt test monitoring | P11 (Elementary) | Test history, freshness, anomaly detection |
| Data quality gates | P11 (Soda Core) | Per-layer quality checks with YAML config |

---

## 10. Decision Tree

```
START: What is your primary need?
|
|-- Batch analytics on files (no streaming needed)
|   --> Pipeline 00: Batch Baseline (dbt + DuckDB)
|       1 service, 2.96M rows in 9s, 91 tests
|
|-- Real-time streaming pipeline
|   |
|   |-- Do you need Iceberg (open table format)?
|   |   |
|   |   |-- YES: Iceberg required
|   |   |   |
|   |   |   |-- Prefer SQL-only development?
|   |   |   |   |-- YES --> Choose broker:
|   |   |   |   |   |-- Want simplest ops? --> P04: Redpanda+Flink+Iceberg
|   |   |   |   |   |   (25K evt/s, 1,860 MB, 6 services)
|   |   |   |   |   |-- Want largest ecosystem? --> P01: Kafka+Flink+Iceberg
|   |   |   |   |       (18.5K evt/s, 2,870 MB, 7 services)
|   |   |   |   |
|   |   |   |   |-- NO (prefer Python API) --> Choose broker:
|   |   |   |       |-- Want lowest memory? --> P05: Redpanda+Spark+Iceberg
|   |   |   |       |   (24.6K evt/s, 917 MB, 5 services)
|   |   |   |       |-- Want fastest processing? --> P02: Kafka+Spark+Iceberg
|   |   |   |           (24.4K evt/s, 1,230 MB, 6 services)
|   |   |
|   |   |-- NO: Iceberg not required
|   |       |
|   |       |-- Want absolute lowest latency + simplest setup?
|   |           |-- Want lowest memory? --> P06: Redpanda+RisingWave
|   |           |   (449 MB, 3 services, ~2s processing)
|   |           |-- Want Kafka ecosystem? --> P03: Kafka+RisingWave
|   |               (687 MB, 4 services, ~2s processing)
|   |
|   |-- Do you need orchestration?
|       |
|       |-- YES: Need workflow orchestration
|       |   |
|       |   |-- Want simplest setup (YAML, no Python)?
|       |   |   --> P07: Kestra (+485 MB, UI at :8083)
|       |   |
|       |   |-- Want largest ecosystem + most operators?
|       |   |   --> P08: Airflow/Astronomer (+1,500 MB, UI at :8080)
|       |   |
|       |   |-- Want best dbt integration + asset lineage?
|       |       --> P09: Dagster (+502 MB, UI at :3000)
|       |
|       |-- NO: No orchestration needed
|           --> Use P01-P06 directly with cron or manual triggers
|
|-- Analytical serving layer (fast queries on large data)
|   --> Pipeline 10: ClickHouse + Metabase/Superset
|       2.76M rows, all queries <50ms
|       |-- Want easy self-service BI? --> Metabase (zero-config)
|       |-- Want power-user SQL BI? --> Superset (SQL Lab)
|
|-- Data quality and observability
    --> Pipeline 11: Elementary + Soda Core
        |-- dbt-native monitoring? --> Elementary (add package, done)
        |-- Cross-pipeline quality gates? --> Soda Core (YAML checks)
```

### Quick-Reference: The Three Sweet Spots

For teams evaluating these pipelines, three configurations stand out as optimal for common scenarios:

**1. Maximum Simplicity** -- Pipeline 06 (Redpanda + RisingWave)
- 3 services, 449 MB memory, ~2s processing
- Pure SQL, no JVM, no JARs, no object storage
- Trade-off: no Iceberg output, smaller ecosystem

**2. Balanced Production** -- Pipeline 04 (Redpanda + Flink + Iceberg)
- 6 services, 1,860 MB memory, 25K evt/s ingestion
- SQL-based, Iceberg output, Redpanda simplicity
- Trade-off: JVM dependency, 27s processing time

**3. Enterprise Standard** -- Pipeline 01 (Kafka + Flink + Iceberg) + Pipeline 09 (Dagster)
- Kafka ecosystem, Flink processing, Iceberg storage, Dagster orchestration
- Maximum tooling support, asset lineage, dbt integration
- Trade-off: 10 services, 2,770 MB, highest complexity

---

*Report based on benchmark verification of all 12 pipelines, February 2026.*
*Streaming pipelines tested with 10,000 events from NYC Yellow Taxi January 2024 dataset.*
*Pipeline 00 tested with full 2,964,624 rows. Pipeline 10 tested with 2,760,000 rows.*
*All measurements taken on the same host under comparable conditions.*

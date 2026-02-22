# Real-Time Data Engineering Documentation

**Project:** 24-Pipeline Streaming Comparison Framework
**Status:** 22/24 PASS, 2 PARTIAL (P11 Elementary/DuckDB, P14 Materialize/dbt), 0 failures
**Latest Benchmark:** 2026-02-22
**Technologies:** Kafka, Flink, Spark, Iceberg, Delta, Hudi, dbt, Dagster, Kestra, and more

---

## Documentation Index

### Learning Resources

#### Complete Walkthrough: P01 (Production Pipeline)
The industry-standard Kafka + Flink + Iceberg + dbt stack -- production-hardened with 94/94 dbt tests.

- **[Interactive Notebook](../notebooks/P01_Complete_Pipeline_Notebook.ipynb)** - 118-cell Jupyter notebook with executable code
- **[Production Guide](P01_PRODUCTION_GUIDE.md)** - Markdown walkthrough for easy reading
- **Status:** 94/94 tests passing, 151s E2E, 5.8GB peak memory

**What You'll Learn:**
1. Architecture design (data plane vs control plane)
2. Kafka event streaming (KRaft mode, idempotent producer, DLQ)
3. Flink real-time transformations (Bronze -> Silver, watermarks, dedup)
4. Iceberg ACID table storage (V3 format, Lakekeeper REST catalog)
5. dbt analytics modeling (Silver -> Gold, 94 tests, source freshness)
6. Monitoring and operations (Prometheus, health checks, consumer lag)

---

### Pipeline Comparison & Benchmarks

#### **[Benchmark Results](../BENCHMARK_RESULTS.md)**
Complete benchmark results for all 24 pipelines with E2E timing, resource usage, and production recommendations.

#### **[Comparison Report](../pipelines/comparison/comparison_report.md)**
Auto-generated multi-tier comparison across all pipelines.

#### **[Results CSV](../pipelines/comparison/results.csv)**
Raw performance data for all 24 benchmarked pipelines.

**Metrics:** E2E timing, ingestion throughput, resource usage, dbt test results.

---

### Architecture & Design

#### **[Real-Time Streaming Data Paths](../real_time_streaming_data_paths.md)**
Comprehensive reference document (2300+ lines) mapping every major real-time technology with benchmark results per stage.

**7 Pipeline Stages (each with benchmark results):**
1. Ingestion (Kafka, Redpanda, Debezium) -- Winner: Redpanda for performance
2. Processing (Flink, Spark, RisingWave, Kafka Streams, Bytewax) -- Winner: Flink 2.0.1
3. Storage (Iceberg, Delta, Hudi, Pinot, Druid) -- Winner: Iceberg 1.10.1
4. Transformation (dbt-duckdb, dbt-spark, dbt-postgres) -- Winner: dbt-duckdb
5. Orchestration (Dagster, Kestra, Airflow, Prefect, Mage) -- Winner: Dagster (109s)
6. Serving (ClickHouse, Pinot, Druid) -- Winner: Druid (70s)
7. Observability (Elementary, Soda, Prometheus) -- Best: Flink metrics + dbt tests

---

### dbt Documentation

Located in: `docs/dbt/`

1. **[dbt Basics](dbt/01_dbt_basics.md)** - Project structure, models, tests
2. **[Incremental Models](dbt/02_incremental_models.md)** - Efficient rebuilds
3. **[Macros & Dispatch](dbt/03_macros_dispatch.md)** - Cross-adapter SQL
4. **[Data Contracts](dbt/04_data_contracts.md)** - Testing & quality
5. **[dbt with Iceberg](dbt/05_dbt_iceberg.md)** - DuckDB integration

---

## Quick Start Guide

### Option 1: Run the Production Pipeline (P01)

```bash
cd pipelines/01-kafka-flink-iceberg
make up              # Start all containers
make create-topics   # Create Kafka topics
make generate        # Produce 10k taxi events
make process         # Run Flink SQL (Bronze + Silver)
make dbt-build       # Run dbt transformations (Gold)
make status          # Check pipeline health
make down            # Tear down
```

### Option 2: Run Full Benchmark

```bash
# Single pipeline benchmark
make benchmark

# From repo root: all 24 pipelines
make benchmark-all

# Generate comparison report
make compare
```

### Option 3: Explore Jupyter Notebook

```bash
pip install jupyter
cd notebooks
jupyter notebook P01_Complete_Pipeline_Notebook.ipynb
```

---

## Repository Structure

```
real_time_data_engineering/
├── docs/                              # You are here
│   ├── README.md                      # This file
│   ├── P01_PRODUCTION_GUIDE.md        # Complete walkthrough
│   └── dbt/                           # dbt-specific docs
│
├── notebooks/                         # Interactive learning
│   └── P01_Complete_Pipeline_Notebook.ipynb
│
├── pipelines/                         # All 24 pipelines
│   ├── 00-batch-baseline/
│   ├── 01-kafka-flink-iceberg/        # Production reference
│   ├── ... (22 more pipelines)
│   └── comparison/                    # Results CSV + report
│
├── shared/                            # Shared components
│   ├── data-generator/                # Parquet -> Kafka producer
│   ├── docker/                        # Base Dockerfiles
│   ├── benchmarks/                    # Benchmark framework
│   └── dbt-models/                    # Canonical dbt models
│
├── BENCHMARK_RESULTS.md               # Complete benchmark results
├── real_time_streaming_data_paths.md  # Technology reference (2300+ lines)
└── README.md                          # Project root readme
```

---

## Learning Paths

### Path 1: Complete Beginner

1. Read [P01 Production Guide](P01_PRODUCTION_GUIDE.md) - Architecture overview
2. Run P01 pipeline following Quick Start above
3. Explore [dbt Basics](dbt/01_dbt_basics.md)
4. Review [Benchmark Results](../BENCHMARK_RESULTS.md) - See what's possible

### Path 2: Data Engineer

1. Clone repo and run P01 benchmark
2. Study [Jupyter Notebook](../notebooks/P01_Complete_Pipeline_Notebook.ipynb) - 118-cell deep dive
3. Read [Real-Time Streaming Data Paths](../real_time_streaming_data_paths.md) - Technology landscape
4. Compare pipelines in [Comparison Report](../pipelines/comparison/comparison_report.md)
5. Modify dbt models and re-run

### Path 3: Platform Engineer

1. Run all Tier 1 pipelines (P00-P06) with benchmarks
2. Study [P01 Production Guide](P01_PRODUCTION_GUIDE.md) - Operations sections
3. Set up monitoring (Prometheus + Grafana)
4. Implement Iceberg maintenance jobs

### Path 4: Architect

1. Read [Real-Time Streaming Data Paths](../real_time_streaming_data_paths.md) - Complete technology map
2. Study [Benchmark Results](../BENCHMARK_RESULTS.md) - Performance trade-offs
3. Design custom pipeline combining best components
4. Explore partial pipelines (P11, P14) for upstream fixes

---

## Benchmark Results Summary (2026-02-22)

From [BENCHMARK_RESULTS.md](../BENCHMARK_RESULTS.md):

| Pipeline | E2E Time | dbt Tests | Status |
|----------|----------|-----------|--------|
| P01 Kafka+Flink+Iceberg | 151s | 94/94 | Production |
| P04 Redpanda+Flink+Iceberg | 147s | 91/91 | Production |
| P09 Dagster Orchestrated | 97s | 91/91 | Production |
| P12 CDC Debezium | 139s | 91/91 | Production |
| P15 Kafka Streams | 115s | n/a | Production |
| P16 Pinot OLAP | 136s | n/a | Production |
| P17 Druid Timeseries | 101s | n/a | Production |
| P20 Bytewax Python | 62s | n/a | Production |
| P23 Full Stack Capstone | 176s | 91/91 | Production |

**Fastest Processing:** RisingWave P03/P06 (2s processing)
**Fastest E2E:** P19 Mage AI (51s), P20 Bytewax (62s)
**Best All-Around:** P01 Kafka+Flink+Iceberg (94/94 tests, production-hardened)

---

## Pipeline Recommendations

Based on [BENCHMARK_RESULTS.md](../BENCHMARK_RESULTS.md):

### Best Overall: P01 Kafka + Flink + Iceberg
- 94/94 dbt tests passing, defense-in-depth data quality
- 151s E2E, production-hardened with idempotent producer, DLQ, watermarks, dedup
- **Use when:** Building enterprise streaming platform

### Best Performance: P03/P06 RisingWave
- Fastest processing: 2s for 10k events, streaming SQL
- **Use when:** Real-time SQL analytics, low-latency queries

### Best Orchestrated: P09 Dagster
- 97s E2E (fastest orchestrated), 91/91 dbt tests
- **Use when:** Asset-centric data platform with lineage

### Best Efficiency: P04 Redpanda + Flink + Iceberg
- 3% faster than P01 (147s vs 151s), 25-35% less memory, same API
- **Use when:** Cost optimization is priority

### Best for CDC: P12 Debezium + Flink + Iceberg
- 139s E2E, 0.3s ingestion via PostgreSQL WAL snapshot
- **Use when:** Capturing database changes in real-time

### Best End-to-End: P23 Full Stack Capstone
- CDC + Flink + Iceberg + dbt + ClickHouse + Grafana
- **Use when:** Complete reference architecture with dashboards

---

## Technical Stack

### Data Plane (Streaming)
- **Event Brokers:** Apache Kafka 4.0 (KRaft), Redpanda
- **Stream Processing:** Apache Flink 2.0.1, Spark 3.3.3, RisingWave, Materialize, Kafka Streams, Bytewax
- **Storage Formats:** Apache Iceberg 1.10.1, Delta Lake 2.2.0, Apache Hudi 0.15.0
- **Object Storage:** MinIO (S3-compatible)
- **REST Catalog:** Lakekeeper v0.11.2

### Control Plane (Orchestration)
- **Workflow:** Dagster, Kestra, Apache Airflow, Prefect, Mage AI
- **Transformation:** dbt Core 1.11 (dbt-duckdb, dbt-spark, dbt-postgres)
- **Testing:** dbt tests (94 in P01), Soda Core, Elementary

### Serving Layer
- **OLAP:** ClickHouse, Apache Pinot, Apache Druid
- **BI:** Superset, Metabase, Grafana
- **Feature Store:** Feast

---

## Contributing

Found a bug? Want to fix a partial pipeline?

1. Review [BENCHMARK_RESULTS.md](../BENCHMARK_RESULTS.md) for current status
2. Check the "Issues Summary" section for fixable items
3. Submit PR with fix + benchmark results

**Priority fixes:**
- P02/P05: dbt-spark `database` config issue
- P13: dbt source path (Iceberg -> Delta)
- P21: Feast column name mismatch
- P22: dbt column name mismatch

---

**Start here:** [P01 Production Guide](P01_PRODUCTION_GUIDE.md)

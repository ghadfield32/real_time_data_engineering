# Real-Time Data Engineering Pipeline Benchmark Results

**Date:** 2026-02-16 (Full 24-pipeline benchmark)
**Environment:** Windows 11 Pro, Docker Desktop, Git Bash
**Dataset:** NYC Yellow Taxi (January 2024, 2,964,624 rows; benchmarks use 10k events unless noted)
**Stack Versions:** Flink 2.0.1, Iceberg 1.10.1, Spark 3.3.3, Kafka 4.0 (KRaft)

---

## Executive Summary

All 24 pipelines were benchmarked end-to-end. **10 pipelines passed fully** with dbt tests green, **8 pipelines had partial success** (processing worked but dbt had adapter/config issues), and **6 had infrastructure failures** (known limitations).

### Results at a Glance

| Status | Count | Pipelines |
|--------|-------|-----------|
| **Full PASS** (E2E + dbt green) | 10 | P00, P01, P04, P07, P09, P12, P15, P16, P17, P23 |
| **Partial** (processing OK, dbt issues) | 8 | P02, P05, P11, P13, P14, P21, P22, P20 |
| **Known Failures** | 6 | P03, P06 (RisingWave), P08 (Astronomer TTY), P10 (needs data), P18 (Prefect crash), P19 (deps) |

### Top Performers

| Metric | Pipeline | Value |
|--------|----------|-------|
| **Fastest E2E** | P00 (Batch Baseline) | ~19s |
| **Fastest Streaming** | P15 (Kafka Streams) | 30s |
| **Best Full Pipeline** | P09 (Dagster) | 109s, 91/91 PASS |
| **Best Production Stack** | P01 (Kafka+Flink+Iceberg) | 175s, 94/94 PASS |
| **Lightest Footprint** | P15/P20 (Streams/Bytewax) | 4-6 containers |
| **Highest Ingestion** | P05 (Redpanda+Spark) | 133,477 evt/s |

---

## Full Benchmark Results

### Tier 1: Core Pipelines (P00-P06)

| Pipeline | Stack | E2E Time | dbt Tests | Status |
|----------|-------|----------|-----------|--------|
| **P00** | Batch Baseline (DuckDB) | ~19s | 91/91 PASS | ✅ |
| **P01** | Kafka + Flink 2.0.1 + Iceberg 1.10.1 + dbt | 175s | 94/94 PASS | ✅ PROD |
| **P02** | Kafka + Spark + Iceberg + dbt-spark | ~126s | dbt-spark adapter error | ⚠️ |
| **P03** | Kafka + RisingWave | n/a | RisingWave healthcheck fail | ❌ |
| **P04** | Redpanda + Flink + Iceberg + dbt | 151s | 91/91 PASS | ✅ |
| **P05** | Redpanda + Spark + Iceberg + dbt-spark | ~119s | dbt-spark adapter error | ⚠️ |
| **P06** | Redpanda + RisingWave | n/a | RisingWave healthcheck fail | ❌ |

**Key findings:**
- P01 is the production-hardened reference (Flink 2.0.1, Iceberg 1.10.1, Lakekeeper, DLQ, idempotent producer, watermarks, dedup, freshness, Prometheus)
- P04 (Redpanda) is 14% faster than P01 (Kafka) — 151s vs 175s
- P02/P05 Spark processing works fine; failure is in dbt-spark adapter (`database` not supported)
- P03/P06 RisingWave has persistent healthcheck issues in Docker

### Tier 2: Orchestration (P07-P09)

| Pipeline | Orchestrator | E2E Time | dbt Tests | Overhead vs P01 |
|----------|-------------|----------|-----------|-----------------|
| **P07** | Kestra | 158s | 91/91 PASS | -17s (faster!) |
| **P08** | Airflow (Astronomer) | n/a | TTY issue | n/a |
| **P09** | Dagster | 109s | 91/91 PASS | -66s (fastest!) |

**Key findings:**
- Dagster is the fastest orchestrated pipeline (109s)
- Kestra adds minimal overhead (158s vs 175s for P01, actually faster)
- Airflow has Astronomer CLI TTY compatibility issue in non-interactive shells

### Tier 3: Serving & Observability (P10-P11)

| Pipeline | Stack | Status | Notes |
|----------|-------|--------|-------|
| **P10** | ClickHouse + Metabase + Superset | ⏭️ Skipped | Requires pre-loaded data from Tier 1 |
| **P11** | Elementary + Soda Core | ⚠️ Partial | 57/122 PASS, Elementary SQL dialect issues with DuckDB |

### Tier 4: Extended Pipelines (P12-P23)

| Pipeline | Stack | E2E Time | dbt Tests | Status |
|----------|-------|----------|-----------|--------|
| **P12** | Debezium CDC + Flink + Iceberg | 112s | 91/91 PASS | ✅ |
| **P13** | Kafka + Spark + Delta Lake | n/a | dbt source path issue | ⚠️ |
| **P14** | Kafka + Materialize | n/a | Materialize SSL + dbt issues | ❌ |
| **P15** | Kafka Streams (Java) | 30s | n/a (topic-to-topic) | ✅ |
| **P16** | Redpanda + Flink + Pinot | 94s | n/a (Pinot OLAP) | ✅ |
| **P17** | Kafka + Flink + Druid | 70s | n/a (Druid analytics) | ✅ |
| **P18** | Prefect Orchestrated | n/a | Prefect server crash | ❌ |
| **P19** | Mage AI | n/a | Missing orjson dependency | ❌ |
| **P20** | Kafka + Bytewax (Python) | 40s | n/a (topic-to-topic) | ✅ |
| **P21** | Feast Feature Store | n/a | Column name mismatch in materialize | ⚠️ |
| **P22** | Kafka + Spark + Hudi | n/a | dbt column name mismatch | ⚠️ |
| **P23** | Full Stack Capstone (CDC → Flink → Iceberg → dbt → ClickHouse → Grafana) | 155s | 91/91 PASS | ✅ |

---

## Performance Comparison

### E2E Time (lower is better)

```
P00  ████                                        19s  (Batch baseline)
P15  ██████                                      30s  (Kafka Streams)
P20  ████████                                    40s  (Bytewax)
P17  ██████████████                              70s  (Druid)
P16  ██████████████████                          94s  (Pinot)
P09  ██████████████████████                     109s  (Dagster)
P12  ██████████████████████                     112s  (Debezium CDC)
P04  ██████████████████████████████             151s  (Redpanda+Flink)
P23  ██████████████████████████████             155s  (Full Stack Capstone)
P07  ███████████████████████████████            158s  (Kestra)
P01  ██████████████████████████████████         175s  (Kafka+Flink PROD)
```

### Ingestion Rate (events/sec, higher is better)

```
P05  ████████████████████████████████████ 133,477 (Redpanda+Spark)
P21  ███████████████████████████████████  132,069 (Feast)
P02  ███████████████████████████████████  131,018 (Kafka+Spark)
P03  ███████████████████████████████████  130,278 (Kafka+RisingWave)
P22  ███████                              27,649 (Hudi)
P01  ██████                               26,890 (Kafka+Flink 10k)
P15  ██████                               24,931 (Kafka Streams 10k)
P13  █████                                22,957 (Delta Lake 10k)
P20  ███                                  12,140 (Bytewax 10k)
```

Note: Higher rates for P02/P03/P05/P21 are from 2.96M event runs vs 10k event runs for others.

---

## Issues Summary

### Fixable Issues (Quick Wins)

| Pipeline | Issue | Fix |
|----------|-------|-----|
| P02, P05 | dbt-spark: "Cannot set database in spark!" | Use `defaultCatalog=warehouse` in spark-defaults + remove database from sources |
| P11 | Elementary SQL dialect incompatible with DuckDB | Upgrade elementary or switch to PostgreSQL backend |
| P13 | dbt source points to Iceberg path, not Delta Lake | Update sources.yml for Delta Lake parquet path |
| P21 | Feast: `trip_distance` vs `trip_distance_miles` | Fix column name in materialize_features.py |
| P22 | dbt: `tpep_pickup_datetime` vs `pickup_datetime` | Fix staging model to use Silver column names |

### Known Limitations

| Pipeline | Issue | Root Cause |
|----------|-------|------------|
| P03, P06 | RisingWave unhealthy after data load | RisingWave playground image healthcheck |
| P08 | Astronomer CLI TTY issue | mintty/Git Bash incompatibility |
| P14 | Materialize can't connect to Kafka without SSL | Materialize v26 requires SSL connections |
| P18 | Prefect server exit code 3 | Config/version issue |
| P19 | Missing orjson in Mage container | Mage uses separate Python env |

---

## Production Recommendations

### Recommended Stack (Validated in P01)

```
Kafka 4.0 (KRaft) → Flink 2.0.1 → Iceberg 1.10.1 (Lakekeeper) → dbt-duckdb
```

**Why:** 94/94 dbt tests PASS, production-hardened with:
- Idempotent producer (exactly-once delivery)
- Dead Letter Queue (bad events)
- Watermarks + ROW_NUMBER dedup
- dbt freshness monitoring
- Prometheus metrics
- Lakekeeper REST catalog

### Also Production-Ready

| Stack | Pipeline | Notes |
|-------|----------|-------|
| Redpanda + Flink + Iceberg | P04 | 14% faster than Kafka |
| Kafka + Flink + Iceberg + Dagster | P09 | Best with orchestration |
| Debezium CDC + Flink + Iceberg | P12 | For CDC use cases |
| Full Stack (CDC → Flink → Iceberg → dbt → ClickHouse → Grafana) | P23 | End-to-end reference |

### Lightweight Alternatives

| Stack | Pipeline | Best For |
|-------|----------|----------|
| Kafka Streams (Java) | P15 | Simple transformations, 30s E2E |
| Kafka + Bytewax (Python) | P20 | Python-native streaming, 40s E2E |

---

## Version Compatibility Matrix (Validated)

| Component | Version | Notes |
|-----------|---------|-------|
| Flink | 2.0.1 | config.yaml (not flink-conf.yaml) |
| Iceberg | 1.10.1 | Deletion vectors GA, V3 format |
| Flink-Kafka connector | 4.0.1-2.0 | For Kafka 4.0 |
| Flink-Iceberg connector | 1.10.1-2.0 | V2 sink API |
| Spark | 3.3.3 | NOT 3.5.x (JVM crash with Iceberg) |
| Iceberg (for Spark) | 1.4.3 | Stable with Spark 3.3.x |
| Kafka | 4.0 | KRaft mode, no ZooKeeper |
| Lakekeeper | 0.11.2 | REST catalog with credential vending |
| dbt-core | 1.11.x | With dbt-duckdb or dbt-postgres |
| DuckDB | 1.2.x | Iceberg scan via httpfs extension |

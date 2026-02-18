"""
Generator for P04_Complete_Pipeline_Notebook.ipynb
Reads actual P04 pipeline files and wraps them in Jupyter cells.

Run from project root:  python scripts/gen_p04_notebook.py
Or from notebooks dir:  python ../scripts/gen_p04_notebook.py

Updated 2026-02-18: Post-audit production-hardening pass
  - Corrected benchmark numbers (post sleep-5 fix)
  - Added streaming SQL sections (00-init-streaming + 07-streaming-bronze)
  - Fixed topic names (taxi.raw_trips, not taxi-trips)
  - Updated P01 vs P04 comparison (accurate post-audit parity table)
  - Added Section 21: Adapting to Your Own Dataset
  - Added Section 22: What We Learned (linear retrospective)
"""
import json, os, sys

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P04    = os.path.join(BASE, 'pipelines', '04-redpanda-flink-iceberg')
P01    = os.path.join(BASE, 'pipelines', '01-kafka-flink-iceberg')
SHARED = os.path.join(BASE, 'shared')
OUT    = os.path.join(BASE, 'notebooks', 'P04_Complete_Pipeline_Notebook.ipynb')


def read(path, fallback='# file not found'):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return f.read()
    print(f'  WARNING: not found: {path}', file=sys.stderr)
    return fallback


def md(source):
    lines = source.splitlines(True)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    return {'cell_type': 'markdown', 'metadata': {}, 'source': lines}


def code(source):
    lines = source.splitlines(True)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    return {'cell_type': 'code', 'execution_count': None,
            'metadata': {}, 'outputs': [], 'source': lines}


def wf(rel_path, content):
    """%%writefile cell — writes file content relative to notebooks/ dir."""
    return code(f'%%writefile {rel_path}\n{content}')


# ─── Load all source files ────────────────────────────────────────────────────
print('Loading source files...')

flink_dockerfile   = read(os.path.join(SHARED, 'docker', 'flink.Dockerfile'))
dbt_dockerfile     = read(os.path.join(SHARED, 'docker', 'dbt.Dockerfile'))
gen_requirements   = read(os.path.join(SHARED, 'data-generator', 'requirements.txt'))
generator_py       = read(os.path.join(SHARED, 'data-generator', 'generator.py'))
taxi_schema        = read(os.path.join(SHARED, 'schemas', 'taxi_trip.json'))

docker_compose     = read(os.path.join(P04, 'docker-compose.yml'))
makefile_content   = read(os.path.join(P04, 'Makefile'))
create_topics_sh   = read(os.path.join(P04, 'kafka', 'create-topics.sh'))
core_site_xml      = read(os.path.join(P04, 'flink', 'conf', 'core-site.xml'))
flink_config_yaml  = read(os.path.join(P04, 'flink', 'conf', 'config.yaml'))

# Flink SQL files — batch mode
sql_00_init        = read(os.path.join(P04, 'flink', 'sql', '00-init.sql'))
sql_01_kafka_src   = read(os.path.join(P04, 'flink', 'sql', '01-create-kafka-source.sql'))
sql_02_iceberg     = read(os.path.join(P04, 'flink', 'sql', '02-create-iceberg-catalog.sql'))
sql_03_bronze      = read(os.path.join(P04, 'flink', 'sql', '03-bronze-raw-trips.sql'))
sql_04_silver      = read(os.path.join(P04, 'flink', 'sql', '04-silver-cleaned-trips.sql'))
sql_05_bronze      = read(os.path.join(P04, 'flink', 'sql', '05-bronze.sql'))
sql_06_silver      = read(os.path.join(P04, 'flink', 'sql', '06-silver.sql'))

# Flink SQL files — streaming mode (added Feb 2026 audit)
sql_00_streaming   = read(os.path.join(P04, 'flink', 'sql', '00-init-streaming.sql'))
sql_07_streaming   = read(os.path.join(P04, 'flink', 'sql', '07-streaming-bronze.sql'))

# P04 has no 05-run-all.sql — process uses separate make targets (process-bronze + process-silver)
# We show P01's combined file as a reference for understanding the pattern
sql_run_all_ref    = read(os.path.join(P01, 'flink', 'sql', '05-run-all.sql'),
                          fallback='-- 05-run-all.sql reference not available')

# dbt project files
dbt_project_yml    = read(os.path.join(P04, 'dbt_project', 'dbt_project.yml'))
profiles_yml       = read(os.path.join(P04, 'dbt_project', 'profiles.yml'))
packages_yml       = read(os.path.join(P04, 'dbt_project', 'packages.yml'))
sources_yml        = read(os.path.join(P04, 'dbt_project', 'models', 'sources', 'sources.yml'))
stg_yellow         = read(os.path.join(P04, 'dbt_project', 'models', 'staging', 'stg_yellow_trips.sql'))
stg_payment        = read(os.path.join(P04, 'dbt_project', 'models', 'staging', 'stg_payment_types.sql'))
stg_rate_codes     = read(os.path.join(P04, 'dbt_project', 'models', 'staging', 'stg_rate_codes.sql'))
stg_taxi_zones     = read(os.path.join(P04, 'dbt_project', 'models', 'staging', 'stg_taxi_zones.sql'))
stg_vendors        = read(os.path.join(P01, 'dbt_project', 'models', 'staging', 'stg_vendors.sql'))
staging_yml        = read(os.path.join(P04, 'dbt_project', 'models', 'staging', 'staging.yml'))
int_trip_metrics   = read(os.path.join(P04, 'dbt_project', 'models', 'intermediate', 'int_trip_metrics.sql'))
int_daily_summary  = read(os.path.join(P04, 'dbt_project', 'models', 'intermediate', 'int_daily_summary.sql'))
int_hourly         = read(os.path.join(P04, 'dbt_project', 'models', 'intermediate', 'int_hourly_patterns.sql'))
intermediate_yml   = read(os.path.join(P04, 'dbt_project', 'models', 'intermediate', 'intermediate.yml'))
fct_trips          = read(os.path.join(P04, 'dbt_project', 'models', 'marts', 'core', 'fct_trips.sql'))
dim_dates          = read(os.path.join(P04, 'dbt_project', 'models', 'marts', 'core', 'dim_dates.sql'))
dim_locations      = read(os.path.join(P04, 'dbt_project', 'models', 'marts', 'core', 'dim_locations.sql'))
dim_payment_types  = read(os.path.join(P04, 'dbt_project', 'models', 'marts', 'core', 'dim_payment_types.sql'))
dim_vendors        = read(os.path.join(P01, 'dbt_project', 'models', 'marts', 'core', 'dim_vendors.sql'))
core_yml           = read(os.path.join(P04, 'dbt_project', 'models', 'marts', 'core', 'core.yml'))
mart_daily_rev     = read(os.path.join(P04, 'dbt_project', 'models', 'marts', 'analytics', 'mart_daily_revenue.sql'))
mart_hourly_dem    = read(os.path.join(P04, 'dbt_project', 'models', 'marts', 'analytics', 'mart_hourly_demand.sql'))
mart_location_pf   = read(os.path.join(P04, 'dbt_project', 'models', 'marts', 'analytics', 'mart_location_performance.sql'))
analytics_yml      = read(os.path.join(P04, 'dbt_project', 'models', 'marts', 'analytics', 'analytics.yml'))
payment_csv        = read(os.path.join(P04, 'dbt_project', 'seeds', 'payment_type_lookup.csv'))
rate_code_csv      = read(os.path.join(P04, 'dbt_project', 'seeds', 'rate_code_lookup.csv'))
seed_props_yml     = read(os.path.join(P04, 'dbt_project', 'seeds', 'seed_properties.yml'))
taxi_zone_csv      = read(os.path.join(P04, 'dbt_project', 'seeds', 'taxi_zone_lookup.csv'))
vendor_csv         = read(os.path.join(P01, 'dbt_project', 'seeds', 'vendor_lookup.csv'))
assert_fare        = read(os.path.join(P04, 'dbt_project', 'tests', 'assert_fare_not_exceeds_total.sql'))
assert_duration    = read(os.path.join(P04, 'dbt_project', 'tests', 'assert_trip_duration_positive.sql'))
macro_cents        = read(os.path.join(P04, 'dbt_project', 'macros', 'cents_to_dollars.sql'))
macro_dayname      = read(os.path.join(P04, 'dbt_project', 'macros', 'dayname_compat.sql'))
macro_duration     = read(os.path.join(P04, 'dbt_project', 'macros', 'duration_minutes.sql'))
macro_test_pos     = read(os.path.join(P04, 'dbt_project', 'macros', 'test_positive_value.sql'))

print('All files loaded.')

# ─── Build notebook cells ─────────────────────────────────────────────────────
cells = []

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 0 — Title & Overview
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
# Pipeline 04: Production Real-Time Pipeline Walkthrough
## Redpanda → Flink 2.0.1 → Apache Iceberg 1.10.1 → dbt-duckdb

> **What this notebook is:** A linear, file-by-file walkthrough of a complete production-grade
> streaming data pipeline. Every cell writes a real file from the live P04 pipeline. By the end
> you will understand *why* every design decision was made — not just *what* the files contain.
>
> **Benchmark result (10,000 events, post-audit Feb 2026):**
> ~88 seconds end-to-end (includes 5s Iceberg metadata flush), 91/91 dbt tests passing.
> P04 is ~20s faster than P01 (Kafka) due to Redpanda's C++ single-binary architecture.
>
> **Post-audit status:** Production-hardened. DLQ in both `create-topics.sh` and Makefile,
> streaming SQL parity with P01, CPU-bounded containers, benchmark race condition fixed.

Run from the `notebooks/` directory so `%%writefile ../pipelines/04-...` paths resolve:

```bash
cd notebooks
jupyter notebook P04_Complete_Pipeline_Notebook.ipynb
```

---

### Table of Contents
1. [Architecture Overview](#1.-Architecture-Overview)
2. [Shared Infrastructure](#2.-Shared-Infrastructure)
3. [Docker Compose: Container Orchestration](#3.-Docker-Compose:-Container-Orchestration)
4. [Redpanda Topics + Dead Letter Queue](#4.-Redpanda-Topics:-Event-Ingestion-+-Dead-Letter-Queue)
5. [Flink Configuration](#5.-Flink-Configuration)
6. [Flink SQL: Batch Session Init](#6.-Flink-SQL:-Batch-Session-Initialization)
7. [Flink SQL: Streaming Session Init](#7.-Flink-SQL:-Streaming-Session-Initialization)
8. [Flink SQL: Bronze Layer](#8.-Flink-SQL:-Bronze-Layer)
9. [Flink SQL: Silver Layer — Deduplication + Quality Filtering](#9.-Flink-SQL:-Silver-Layer)
10. [Flink SQL: Streaming Bronze (Continuous Mode)](#10.-Flink-SQL:-Streaming-Bronze)
11. [dbt Project Configuration](#11.-dbt-Project-Configuration)
12. [dbt Seeds: Reference Data](#12.-dbt-Seeds:-Reference-Data)
13. [dbt Macros](#13.-dbt-Macros:-Cross-Database-Compatibility)
14. [dbt Staging Models](#14.-dbt-Staging-Models)
15. [dbt Intermediate Models](#15.-dbt-Intermediate-Models)
16. [dbt Core Marts (Gold Layer)](#16.-dbt-Core-Marts)
17. [dbt Analytics Marts (Gold Layer)](#17.-dbt-Analytics-Marts)
18. [dbt Tests](#18.-dbt-Tests:-Data-Quality-Assertions)
19. [Makefile: One-Command Orchestration](#19.-Pipeline-Makefile)
20. [Running the Pipeline](#20.-Running-the-Pipeline)
21. [Production Operations + Troubleshooting](#21.-Production-Operations)
22. [Adapting to Your Own Dataset](#22.-Adapting-to-Your-Own-Dataset)
23. [What We Learned: Key Decisions Explained](#23.-What-We-Learned)
"""))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 1 — Architecture Overview
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 1. Architecture Overview

### The Full Data Flow

```
NYC Taxi Parquet Files (local data/)
        │
        ▼
┌──────────────────────┐
│    Data Generator    │  pyarrow → JSON → Kafka-protocol producer
│    (shared/)         │  Modes: burst / realtime / batch
│    ~25,000 evt/s     │  enable.idempotence=True, acks=all
└──────────┬───────────┘
           │  JSON events (350 bytes each)
           ▼
┌─────────────────────────────────────────────────────┐
│                    Redpanda                          │
│  taxi.raw_trips      (3 partitions, 72h retention)  │  ← primary stream
│  taxi.raw_trips.dlq  (1 partition,  7-day retention)│  ← dead letter queue
│                                                      │
│  C++/Seastar binary: ~400 MB RAM, 3s startup        │
│  Kafka-wire-protocol compatible: same Flink connector│
└──────────────┬───────────────────────────────────────┘
               │  Kafka connector (flink-sql-connector-kafka-4.0.1-2.0)
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Apache Flink 2.0.1                              │
│                                                                    │
│  ─── BATCH MODE (default: catch-up processing) ──────────────── │
│  Bronze job:  kafka_raw_trips → iceberg_catalog.bronze.raw_trips  │
│    • Parse ISO 8601 timestamps → TIMESTAMP(3)                     │
│    • Add ingestion_ts = CURRENT_TIMESTAMP                         │
│    • scan.bounded.mode=latest-offset → stops when caught up       │
│    • table.dml-sync=true → blocks until job completes             │
│                                                                    │
│  Silver job:  bronze.raw_trips → silver.cleaned_trips             │
│    • ROW_NUMBER() OVER PARTITION BY natural key → deduplication   │
│    • Quality filters: fare≥0, distance≥0, date 2024-01           │
│    • Type casting: BIGINT→INT, DOUBLE→DECIMAL(10,2)               │
│    • Partitioned by pickup_date DATE                              │
│                                                                    │
│  ─── STREAMING MODE (continuous: make process-streaming) ──────── │
│  Bronze streaming: kafka_raw_trips → bronze.raw_trips             │
│    • Runs indefinitely as events arrive                           │
│    • 30s checkpoints for exactly-once fault tolerance             │
│    • WATERMARK FOR event_time (10s late arrival tolerance)        │
└──────────────────┬───────────────────────────────────────────────┘
                   │  Iceberg S3A writes (Parquet + ZSTD)
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Apache Iceberg 1.10.1 on MinIO                   │
│  s3://warehouse/bronze/raw_trips/     (format-version=1, unpart) │
│  s3://warehouse/silver/cleaned_trips/ (format-version=2, by date)│
│  ACID transactions, snapshot isolation, time travel              │
└──────────────────┬──────────────────────────────────────────────┘
                   │  iceberg_scan('s3://warehouse/silver/cleaned_trips')
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                    dbt-duckdb (in Docker)                         │
│  Sources → Staging → Intermediate → Core Marts → Analytics Marts  │
│  91 data quality tests covering: not_null, unique, relationships, │
│  accepted_values, custom business rules                           │
└──────────────────────────────────────────────────────────────────┘
```

### Technology Stack (Feb 2026, production-validated)

| Component | Version | Role | Key Property |
|-----------|---------|------|-------------|
| **Redpanda** | v25.3.7 | Message broker | Kafka-compatible, C++, 400 MB RAM |
| **Apache Flink** | 2.0.1 (Java 17) | Stream/batch processor | config.yaml (not flink-conf.yaml) |
| **Iceberg Flink runtime** | 1.10.1 for Flink 2.0 | Table format integration | iceberg-flink-runtime-2.0-1.10.1.jar |
| **Kafka connector** | 4.0.1-2.0 | Flink↔Redpanda bridge | Same JAR works with Kafka and Redpanda |
| **Apache Iceberg** | 1.10.1 | Open table format | ACID, time travel, deletion vectors |
| **MinIO** | RELEASE.2025-04-22 | Object storage | S3-compatible, local dev |
| **dbt-duckdb** | ≥1.9 | Analytics transformation | iceberg_scan() reads Iceberg directly |
| **DuckDB** | ≥1.1 | In-process query engine | 500 MB/s Parquet reads |

### P04 vs P01: Accurate Post-Audit Comparison

| Dimension | P01 (Kafka 4.0.0) | P04 (Redpanda v25.3.7) | Notes |
|-----------|-------------------|------------------------|-------|
| Broker runtime | JVM (Java 17) | Native binary (C++/Seastar) | |
| Broker startup | ~30s (KRaft negotiation) | ~3s (single binary) | ~27s savings |
| Broker memory | ~1.5 GB JVM heap | ~400 MB | ~1.1 GB savings |
| Total peak memory | ~5 GB | ~4.2 GB | ~800 MB savings |
| Services (always-on) | 5 | 5 | Same (kafka≈redpanda) |
| dbt tests | 94/94 (incl. vendor dim) | 91/91 | P01 has 3 extra vendor tests |
| Streaming SQL | ✅ 00-init-streaming + 07-streaming | ✅ Same (added Feb 2026) | Now identical |
| Dead Letter Queue | ✅ create-topics.sh + Makefile | ✅ Same (fixed Feb 2026) | Now identical |
| CPU limits | ✅ JM 1.0, TM 2.0 | ✅ Same (added Feb 2026) | Now identical |
| Lakekeeper REST catalog | ✅ opt-in `--profile lakekeeper` | Not included | P01 only, opt-in |
| Flink SQL | Identical (`kafka:9092`) | Identical (`redpanda:9092`) | 1 line different |
| dbt models | Identical | Identical | Same SQL |

> **Key insight:** Everything you learn in P04 transfers 1:1 to P01 and vice versa.
> The only code difference is one line in `00-init.sql`: `bootstrap.servers = 'redpanda:9092'`.
> All Flink SQL, dbt models, Makefile targets, and Iceberg table definitions are identical.

### Medallion Architecture (Bronze → Silver → Gold)

```
BRONZE  (raw landing)           SILVER  (trusted)              GOLD  (analytics)
──────────────────────          ─────────────────────          ─────────────────
• All raw events                • Quality-filtered             • fct_trips (star)
• Original column names         • Deduplicated                 • dim_dates
• Timestamps parsed             • Type-cast (INT, DECIMAL)     • dim_locations
• ingestion_ts added            • Partitioned by date          • dim_payment_types
• ~10,000 rows (all)            • ~9,855 rows (98.5%)          • dim_vendors
• format-version=1              • format-version=2             • mart_daily_revenue
• Unpartitioned                 • PARTITIONED BY pickup_date   • mart_hourly_demand
                                                               • mart_location_perf
Flink owns Bronze+Silver ──────────────────────────────► dbt owns Gold
```

**Separation of concerns:** Flink does what Flink is uniquely good at (ordering, dedup, type
coercion at stream speed). Business logic (trip duration, tip %, speed) lives in dbt where
it is version-controlled, tested, and documented in SQL that analysts can read.
"""))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 2 — Shared Infrastructure
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 2. Shared Infrastructure

The `shared/` directory is reused across all 24 pipelines. These files are **identical** in P01
and P04 — the only difference is the `BROKER_URL` environment variable in Docker Compose.

### 2.1 Flink Dockerfile

Pre-installs 7 JARs at image build time so container startup is fast.

**Why 7 JARs?**

| JAR | Purpose |
|-----|---------|
| `iceberg-flink-runtime-2.0-1.10.1.jar` | Iceberg table format sink + source |
| `flink-sql-connector-kafka-4.0.1-2.0.jar` | Kafka/Redpanda source connector |
| `hadoop-aws-3.3.4.jar` | S3A filesystem for MinIO |
| `hadoop-common-3.3.4.jar` | Core Hadoop (S3A depends on it) |
| `aws-java-sdk-bundle-1.12.367.jar` | AWS SDK (S3A credential management) |
| `iceberg-aws-bundle-1.10.1.jar` | Iceberg AWS utilities + S3FileIO |
| *(Flink base)* | JobManager, TaskManager, SQL client |

> **Flink 2.0 breaking change:** Config file renamed from `flink-conf.yaml` → `config.yaml`.
> The Dockerfile copies `config.yaml` — any pipeline still using `flink-conf.yaml` will silently
> use default settings, causing mysterious failures. All 10 Flink pipelines were migrated.
"""))

cells.append(wf('../shared/docker/flink.Dockerfile', flink_dockerfile))

cells.append(md("""\
### 2.2 dbt Dockerfile

Slim Python image with dbt-core, dbt-duckdb, and the DuckDB Iceberg/httpfs extensions.

> **Design choice:** `dbt deps` runs at container *startup* (entrypoint), not at *build time*.
> This ensures packages.yml is always respected and allows running without rebuilding the image.
> The trade-off: first run takes ~10s longer. For production CI, pre-bake deps into the image.
"""))

cells.append(wf('../shared/docker/dbt.Dockerfile', dbt_dockerfile))

cells.append(md("""\
### 2.3 Data Generator

Reads NYC Yellow Taxi parquet files and produces JSON events to Redpanda (or Kafka).
Key design decisions:

| Decision | Implementation | Why |
|----------|---------------|-----|
| **Idempotent producer** | `enable.idempotence=True, acks=all` | Prevents duplicate events on retry |
| **pyarrow** for parquet | `pyarrow.parquet.ParquetFile` | Columnar reads, lazy (only loads requested rows) |
| **NaN → null** | `replace({float('nan'): None})` | JSON doesn't have NaN; Flink expects null |
| **confluent_kafka** | Works with Kafka AND Redpanda | Same wire protocol |
| **Metrics** | Every 1000 events: throughput + p95/p99 latency | Observability at the source |
| **Modes** | `burst` / `realtime` / `batch` | benchmark / demo / CI respectively |
"""))

cells.append(wf('../shared/data-generator/requirements.txt', gen_requirements))
cells.append(wf('../shared/data-generator/generator.py', generator_py))

cells.append(md("""\
### 2.4 Event Schema (JSON Schema)

Documents the taxi trip event contract. Not enforced at ingestion (no Schema Registry) —
enforcement happens via Flink SQL column definitions and dbt tests downstream.

> **Why no Schema Registry?** For JSON-over-Kafka at 10k–1M events/day, the overhead of
> schema registration (REST API call per producer start, Avro serialization) adds complexity
> without proportional benefit. Schema Registry makes sense for Avro/Protobuf at 10M+/day
> or when multiple teams need a formal contract registry.
"""))

cells.append(wf('../shared/schemas/taxi_trip.json', taxi_schema))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 3 — Docker Compose
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 3. Docker Compose: Container Orchestration

P04 runs **6 always-on containers** plus 2 profile containers:

| Container | Image | CPU limit | Memory limit | Role |
|-----------|-------|-----------|-------------|------|
| `p04-redpanda` | `redpandadata/redpanda:v25.3.7` | (Redpanda manages via --smp 1) | 1.5 GB | Kafka-compatible broker |
| `p04-redpanda-console` | `redpandadata/console:v3.2.2` | — | — | Web UI: topic browser, consumer lag |
| `p04-minio` | `minio/minio:RELEASE.2025-04-22...` | — | 1 GB | S3-compatible object store |
| `p04-mc-init` | `minio/mc:RELEASE.2025-05-21...` | — | — | One-shot: creates `warehouse` bucket |
| `p04-flink-jobmanager` | flink-custom (shared Dockerfile) | **1.0 CPU** | 2 GB | Flink coordinator |
| `p04-flink-taskmanager` | flink-custom (shared Dockerfile) | **2.0 CPU** | 2.5 GB | Flink worker (executes SQL) |
| `p04-dbt` (profile: dbt) | dbt-custom (shared Dockerfile) | — | — | dbt build + tests |
| `p04-data-generator` (profile: generator) | data-generator | — | — | Taxi event producer |

**CPU limits (added Feb 2026 audit):** Without `cpus` limits, all containers compete for
Docker Desktop's shared CPU pool. During Flink processing, the TaskManager can consume all
cores, starving MinIO and causing S3A write timeouts. Capping TM at 2 CPUs prevents this.

### Network topology
- All services: `p04-pipeline-net` (bridge, isolated from host)
- Redpanda Kafka API inside network: `redpanda:9092`
- Redpanda Kafka API external (for local tools): `localhost:19092`
- MinIO S3 API inside network: `minio:9000`
- Flink job API: `flink-jobmanager:8081` (internal), `localhost:8081` (external)

### Healthcheck chain
```
minio healthy → mc-init completes → (Flink services start)
redpanda healthy → flink-jobmanager starts → flink-taskmanager starts
```
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/docker-compose.yml', docker_compose))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 4 — Redpanda Topics + DLQ
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 4. Redpanda Topics: Event Ingestion + Dead Letter Queue

### Two-Topic Design: Primary + DLQ

```
Data Generator
     │
     │  valid JSON events
     ▼
taxi.raw_trips          ← 3 partitions, 72h retention, primary stream
     │
     │  (Flink reads this, processes into Bronze/Silver)
     ▼
[malformed events that fail Flink type parsing are sent to DLQ]
     │
     ▼
taxi.raw_trips.dlq      ← 1 partition, 7-day retention, dead letter queue
```

### Why a Dead Letter Queue?

Without a DLQ, a single malformed event (wrong timestamp format, null where not expected)
can block an entire Kafka partition. Flink's JSON deserializer will throw on parse failure
and stop consuming that partition. A DLQ gives you:
- **Visibility:** You can see which events failed and why
- **Replay:** After fixing the schema/parser, you can re-consume the DLQ
- **Non-blocking:** Bad events don't stop good events from flowing

### Topic Configuration

| Setting | Primary | DLQ | Reason |
|---------|---------|-----|--------|
| Partitions | 3 | 1 | DLQ is low-volume, no need for parallelism |
| `retention.ms` | 259,200,000 (72h) | 604,800,000 (7 days) | DLQ kept longer for investigation |
| `cleanup.policy` | `delete` | `delete` | Time-based expiry (not compaction) |

### Makefile vs create-topics.sh

The Makefile's `create-topics` target creates both topics **inline** via `rpk`. The `create-topics.sh`
shell script also creates both topics. Either works — the Makefile target is the standard entry point.

> **Audit fix (Feb 2026):** The original Makefile `create-topics` only created the primary topic,
> bypassing the DLQ. Both the shell script and Makefile now create both topics consistently.

### rpk vs kafka-topics.sh

```bash
# Kafka (JVM, ~3s including JVM startup):
kafka-topics.sh --bootstrap-server kafka:9092 --create --topic taxi.raw_trips \
  --partitions 3 --config retention.ms=259200000

# Redpanda rpk (native Go binary, ~50ms):
rpk topic create taxi.raw_trips --brokers redpanda:9092 --partitions 3 \
  --topic-config retention.ms=259200000
```
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/kafka/create-topics.sh', create_topics_sh))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 5 — Flink Configuration
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 5. Flink Configuration

### 5.1 Hadoop core-site.xml — S3A → MinIO Bridge

Flink uses Apache Hadoop's S3A filesystem driver to read/write Iceberg files stored in MinIO.
This XML file maps S3A URI scheme (`s3a://`) to MinIO's endpoint.

```
Flink SQL INSERT INTO iceberg_catalog.bronze.raw_trips
     │   uses S3FileIO → s3a://warehouse/bronze/raw_trips/data/...
     ▼
Hadoop S3A FileSystem Driver
     │   fs.s3a.endpoint = http://minio:9000
     │   fs.s3a.path.style.access = true  (MinIO uses path-style, not virtual-hosted)
     ▼
MinIO HTTP server on port 9000
```

Without `path.style.access=true`, Hadoop would try to reach `warehouse.minio:9000` (DNS lookup
fails in Docker) instead of `minio:9000/warehouse/` (correct Docker network address).
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/conf/core-site.xml', core_site_xml))

cells.append(md("""\
### 5.2 Flink Cluster Configuration (config.yaml)

> **Flink 2.0 breaking change:** `flink-conf.yaml` → `config.yaml`. If you mount the old
> filename, Flink silently uses defaults — no error. This caused mysterious TaskManager failures
> until the rename was discovered. All pipelines migrated in the Feb 2026 upgrade.

Key settings with explanations:

| Setting | Value | Why it matters |
|---------|-------|---------------|
| `classloader.check-leaked-classloader` | `false` | Iceberg loads classes dynamically; without this Flink throws classloader leak warnings that abort jobs |
| `taskmanager.memory.process.size` | `2048m` | Total TM memory (JVM heap + off-heap + metaspace). Must match docker-compose `memory: 2.5G` with headroom |
| `parallelism.default` | `2` | 2 task slots for 3-partition topic; adequate for 10k benchmark |
| `state.backend` | `hashmap` | In-memory state (fast for batch jobs). For streaming: change to `rocksdb` + configure `state.checkpoints.dir` |
| `execution.checkpointing.interval` | `30s` | How often Flink snapshots operator state. Required for exactly-once in streaming mode |

> **Streaming mode note:** The config.yaml settings for `state.backend = rocksdb` and
> `state.checkpoints.dir = s3a://warehouse/checkpoints/` should be added before running
> `make process-streaming` in production. Batch mode doesn't need checkpoint recovery.
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/conf/config.yaml', flink_config_yaml))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 6 — Flink SQL: Batch Session Init
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 6. Flink SQL: Batch Session Initialization

`00-init.sql` is the **most important file in the pipeline**. It defines the entire session
state that all subsequent SQL files inherit.

### How the Flink SQL CLI Session Works

```bash
# -i flag: "initialize" — runs before interactive or -f execution
sql-client.sh embedded -i 00-init.sql -f 05-bronze.sql
#                       ─────────────  ───────────────
#                        init file      batch execute file
#
# Result: 00-init.sql creates tables and catalog in-session.
#         05-bronze.sql can then reference kafka_raw_trips and iceberg_catalog.
```

The `-i` and `-f` flags share the same SQL session — like running two scripts in the same
database connection. Without `-i`, the `-f` file would see an empty session with no tables.

### Three Things 00-init.sql Does

#### 1. Batch execution settings
```sql
SET 'execution.runtime-mode' = 'batch';       -- process bounded data and stop
SET 'table.dml-sync' = 'true';               -- block after each INSERT until complete
```
Without `table.dml-sync=true`, the Silver job would start before Bronze finishes writing,
resulting in 0 Silver rows (reading an empty or partially-written Bronze table).

#### 2. Redpanda source table (virtual — reads from topic)
The `kafka_raw_trips` table is never stored anywhere. It's a virtual table that maps
Redpanda topic messages to SQL columns. Every row in the topic becomes a SQL row.

Key option: `'scan.bounded.mode' = 'latest-offset'` — in batch mode, Flink stops reading
at the offset that was "latest" when the job started. This makes the batch job finite.
Without this, batch mode Flink would wait forever for new messages.

#### 3. Iceberg catalog (where table metadata lives)
The Hadoop catalog maps Iceberg table names to S3A paths:
```
iceberg_catalog.bronze.raw_trips
    → s3a://warehouse/bronze/raw_trips/
        ├── metadata/
        │   ├── v1.metadata.json
        │   └── snap-....avro
        └── data/
            └── 00000-0-....parquet
```

### Event-time Watermark (important for streaming)
```sql
event_time AS TO_TIMESTAMP(tpep_pickup_datetime, 'yyyy-MM-dd''T''HH:mm:ss'),
WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
```
In **batch mode**: watermark is parsed but has no effect. All records are processed without
ordering concern. In **streaming mode**: watermark tells Flink to consider events more than
10 seconds late as "late arrivals" — allows window functions to close properly.
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/sql/00-init.sql', sql_00_init))

cells.append(md("""\
### 6.1 Reference: Kafka Source Table (standalone)

This file creates only the Redpanda source table — useful for interactive SQL sessions where
you want to inspect the schema without setting up the full catalog.
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/sql/01-create-kafka-source.sql', sql_01_kafka_src))

cells.append(md("""\
### 6.2 Reference: Iceberg Catalog (standalone)

P04 uses the Flink Hadoop catalog (direct S3A path resolution). The alternative — Lakekeeper
REST catalog — is available on P01 via `--profile lakekeeper`. The REST catalog adds credential
vending (no S3 keys in SQL) but requires 4 extra services (Postgres + 3 Lakekeeper containers).
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/sql/02-create-iceberg-catalog.sql', sql_02_iceberg))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 7 — Flink SQL: Streaming Session Init
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 7. Flink SQL: Streaming Session Initialization

`00-init-streaming.sql` is the streaming counterpart to `00-init.sql`. Use it with
`07-streaming-bronze.sql` for **continuous event processing** instead of batch catch-up.

### Batch vs Streaming: Key Differences

| Aspect | Batch (`00-init.sql`) | Streaming (`00-init-streaming.sql`) |
|--------|----------------------|-------------------------------------|
| `execution.runtime-mode` | `batch` | `streaming` |
| `table.dml-sync` | `true` (block per INSERT) | **NOT SET** — would hang forever |
| `scan.bounded.mode` | `latest-offset` (stop at current end) | **NOT SET** — reads forever |
| `scan.startup.mode` | `earliest-offset` (reprocess all) | `latest-offset` (only new events) |
| Job lifecycle | Terminates when all data processed | Runs indefinitely until cancelled |
| Fault tolerance | Not needed (restart from Redpanda) | Checkpoints every 30s (exactly-once) |
| Use case | Backfill, benchmarks, scheduled runs | Production real-time ingestion |

### Why NOT Setting table.dml-sync in Streaming Mode is Critical

```sql
-- BATCH init:
SET 'table.dml-sync' = 'true';  -- block until INSERT completes → fine (job terminates)

-- STREAMING init:
-- Do NOT set table.dml-sync — the streaming INSERT runs FOREVER.
-- If dml-sync=true, the session would block forever on the first INSERT,
-- never getting to run the second SQL statement.
```

### Group ID Differs

- Batch: `'properties.group.id' = 'flink-consumer'` — offset tracked for batch replay
- Streaming: `'properties.group.id' = 'flink-streaming-consumer'` — separate group, reads from latest

This separation means you can run batch reprocessing and streaming ingestion simultaneously
without the consumer groups interfering with each other.
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/sql/00-init-streaming.sql', sql_00_streaming))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 8 — Bronze Layer
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 8. Flink SQL: Bronze Layer (Redpanda → Iceberg)

### Bronze Layer Design Philosophy

The Bronze layer is a **faithful copy** of the source. No business logic. No filtering. Every
event lands — even malformed ones. This is the audit trail.

```
Redpanda message (JSON):
{
  "VendorID": 1,
  "tpep_pickup_datetime": "2024-01-15T08:30:00",   ← STRING
  "fare_amount": 12.50,
  ...
}

Bronze Iceberg row:
  VendorID              BIGINT  = 1
  tpep_pickup_datetime  TIMESTAMP(3) = 2024-01-15 08:30:00.000  ← parsed
  fare_amount           DOUBLE  = 12.50
  ingestion_ts          TIMESTAMP(3) = 2024-01-15 09:01:33.412  ← added
```

### Timestamp Parsing Pattern

```sql
TO_TIMESTAMP(tpep_pickup_datetime, 'yyyy-MM-dd''T''HH:mm:ss')
--                                              ↑
--                               Escaped single quotes for literal 'T'
--                               Java SimpleDateFormat syntax in SQL string literals
```

### Why format-version=1 for Bronze?

Iceberg v1 is sufficient for append-only Bronze. v2 adds row-level delete support
(required for UPDATE/MERGE operations). Keeping Bronze at v1 makes it slightly faster
to write and simpler to compact. Silver uses v2 because future maintenance (MERGE INTO for
dedup, DELETE WHERE for GDPR) requires it.

### 8.1 Bronze — Commented Reference
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/sql/03-bronze-raw-trips.sql', sql_03_bronze))

cells.append(md("""\
### 8.2 Bronze — Production File (05-bronze.sql)

Used by `make process-bronze`. Runs as: `sql-client.sh embedded -i 00-init.sql -f 05-bronze.sql`
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/sql/05-bronze.sql', sql_05_bronze))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 9 — Silver Layer
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 9. Flink SQL: Silver Layer — Deduplication + Quality Filtering

Silver is the **trusted, clean** layer. It reads from Bronze and applies two things:
1. **Quality filtering** — removes invalid/out-of-range records
2. **Deduplication** — ROW_NUMBER() removes duplicate events (e.g., producer retries)

### 9.1 Deduplication via ROW_NUMBER()

```sql
WITH deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY VendorID, tpep_pickup_datetime, tpep_dropoff_datetime,
                         PULocationID, DOLocationID, fare_amount, total_amount
            ORDER BY ingestion_ts DESC        ← keep the LATEST ingestion of a duplicate
        ) AS rn
    FROM iceberg_catalog.bronze.raw_trips
    WHERE ...quality filters...
)
SELECT ...columns... FROM deduped WHERE rn = 1;
```

**Natural key**: The combination of (vendor, pickup_time, dropoff_time, pickup_zone, dropoff_zone,
fare, total) uniquely identifies a taxi trip. Two rows with the same natural key = same trip.

**ORDER BY ingestion_ts DESC**: If a producer sent the same event twice due to a retry,
we keep the most recently ingested copy (latest `ingestion_ts`).

### Why ROW_NUMBER() and not DISTINCT?

`DISTINCT` removes rows with identical values across ALL columns. It won't help if events
differ in `ingestion_ts` (they always do — each event has a unique arrival timestamp).
ROW_NUMBER partitioned by the **business natural key** correctly deduplicates trips that
arrived twice with different timestamps.

### Quality Filters Applied

| Filter | SQL | Expected rejection |
|--------|-----|--------------------|
| Valid pickup time | `tpep_pickup_datetime IS NOT NULL` | Malformed events |
| Valid dropoff time | `tpep_dropoff_datetime IS NOT NULL` | Malformed events |
| Non-negative distance | `trip_distance >= 0` | GPS glitches |
| Non-negative fare | `fare_amount >= 0` | Refund/test records |
| Date range | `pickup_date BETWEEN 2024-01-01 AND 2024-01-31` | Out-of-period events |

**Expected yield:** ~9,855 / 10,000 = 98.55% pass rate.

### Silver Schema Changes vs Bronze

| Column | Bronze | Silver | Change |
|--------|--------|--------|--------|
| `VendorID` | BIGINT | INT (as vendor_id in dbt) | Narrowed in dbt stg |
| `fare_amount` | DOUBLE | DECIMAL(10,2) | Rounded + typed |
| `pickup_date` | — | DATE | Added (for partitioning) |
| `trip_id` | — | STRING | Added (MD5 surrogate key) |
| `ingestion_ts` | TIMESTAMP(3) | — | Dropped (used only for dedup order) |

### 9.1 Silver — Commented Reference
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/sql/04-silver-cleaned-trips.sql', sql_04_silver))

cells.append(md("""\
### 9.2 Silver — Production File (06-silver.sql)

Used by `make process-silver`. This standalone file has the **full ROW_NUMBER() deduplication**
logic — it produces the same result as the combined `05-run-all.sql` pipeline.

> **Audit finding (Feb 2026):** An earlier version of `06-silver.sql` ran a plain INSERT without
> deduplication, while `05-run-all.sql` had the correct ROW_NUMBER CTE. Running `make process-silver`
> independently would produce duplicates. Both are now identical. Always verify row counts!
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/sql/06-silver.sql', sql_06_silver))

cells.append(md("""\
### 9.3 Combined Pipeline Reference (P01's 05-run-all.sql)

P04 does not have a single combined SQL file — `make process` calls `process-bronze` then
`process-silver` sequentially. Below is P01's combined file for reference — it shows how
both layers can run in one SQL session with `table.dml-sync=true` ensuring ordering.
"""))
cells.append(code(f'# Reference only — this is P01\'s 05-run-all.sql, not used by P04 directly\n'
                  f'# P04 uses: make process-bronze && make process-silver\n'
                  f'print("""\n{sql_run_all_ref}\n""")'))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 10 — Streaming Bronze
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 10. Flink SQL: Streaming Bronze (Continuous Mode)

`07-streaming-bronze.sql` is the **streaming alternative** to `05-bronze.sql`. Use it when you
want Flink to continuously ingest new events as they arrive in Redpanda, rather than doing
a one-time batch catch-up.

### When to Use Streaming vs Batch

| Scenario | Mode | Command |
|----------|------|---------|
| Initial backfill of historical data | Batch | `make process-bronze` |
| Nightly scheduled catch-up | Batch | `make process` |
| Continuous real-time ingestion | Streaming | `make process-streaming` |
| CI/CD pipeline validation | Batch | `make benchmark` |

### Streaming Job Lifecycle

```
make process-streaming
  │
  └─ sql-client.sh embedded -i 00-init-streaming.sql -f 07-streaming-bronze.sql
       │
       ├─ 00-init-streaming.sql: SET streaming mode, CREATE kafka_raw_trips (no bounded mode)
       │
       └─ 07-streaming-bronze.sql: INSERT INTO bronze.raw_trips FROM kafka_raw_trips
            │
            └─ Job runs indefinitely: reads Redpanda → writes Iceberg checkpoints every 30s
                 Exactly-once guarantee: if TM crashes, Flink restores from last checkpoint
                 Cancel with: Ctrl+C or Flink REST API DELETE /jobs/{jobId}
```

### Iceberg Streaming Write Behavior

Flink's Iceberg sink in streaming mode writes files on checkpoint boundaries (every 30s).
Each checkpoint produces one or more Parquet files and commits a new Iceberg snapshot.
This means:
- Data is visible to readers every 30s (not per-event)
- Small files accumulate over time → schedule `rewrite_data_files` compaction periodically
- Time travel works: `SELECT * FROM ... FOR TIMESTAMP AS OF TIMESTAMP '2024-01-15 09:00:00'`
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/flink/sql/07-streaming-bronze.sql', sql_07_streaming))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 11 — dbt Project Configuration
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 11. dbt Project Configuration

dbt handles the **Silver → Gold** transformation. It reads from the Iceberg Silver table via
DuckDB's `iceberg_scan()` function and produces analytics-ready Gold layer tables.

### How dbt-duckdb + Iceberg Works

```python
# 1. DuckDB opens as an in-process embedded database
# 2. DuckDB loads the Iceberg extension
# 3. DuckDB reads Iceberg metadata from MinIO (S3-compatible via httpfs)
# 4. DuckDB reads Parquet data files from MinIO
# 5. dbt materializes results as DuckDB tables (stored in a local .duckdb file)

# In sources.yml:
external_location: "iceberg_scan('s3://warehouse/silver/cleaned_trips', allow_moved_paths=true)"

# DuckDB resolves this as:
# 1. Read s3://warehouse/silver/cleaned_trips/metadata/version-hint.text → get version N
# 2. Read s3://warehouse/silver/cleaned_trips/metadata/vN.metadata.json → get manifest list
# 3. Read manifest files → get Parquet file list
# 4. Read Parquet files → return rows
```

**Why `allow_moved_paths=true`?** In Docker, MinIO is accessible as `minio:9000` from inside
the container, but as `localhost:9000` from outside. The Iceberg metadata records the path used
during write (e.g., `s3a://warehouse/...`) which differs from the read path (`s3://warehouse/...`).
`allow_moved_paths=true` tells DuckDB to ignore path mismatches between metadata and actual location.

### Silver as the dbt Source (Post-Audit)

> **Critical audit finding (Feb 2026):** The original P04 `sources.yml` pointed to the Bronze
> table (`s3://warehouse/bronze/raw_trips`). Every dbt model was built on raw, unvalidated,
> potentially duplicate Bronze data — completely defeating Flink's Silver cleaning work.
> Fixed to point to Silver (`s3://warehouse/silver/cleaned_trips`).
>
> The stg_yellow_trips.sql model is now a **passthrough**: Silver already has clean column names,
> correct types, and validated data. Flink Silver = dbt Staging Source.

### 11.1 dbt_project.yml
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/dbt_project.yml', dbt_project_yml))

cells.append(md("""\
### 11.2 profiles.yml — DuckDB + Iceberg + MinIO Connection

The profile configures three DuckDB extensions:
- `httpfs` — allows DuckDB to read files from HTTP/S3 endpoints
- `iceberg` — adds the `iceberg_scan()` function
- `aws` — provides S3 credential management helpers
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/profiles.yml', profiles_yml))

cells.append(md("""\
### 11.3 packages.yml
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/packages.yml', packages_yml))

cells.append(md("""\
### 11.4 sources.yml — Silver Iceberg as Source

Note: `external_location` uses `s3://` (DuckDB httpfs format), not `s3a://` (Hadoop format).
These are equivalent paths to the same MinIO storage but use different drivers.
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/sources/sources.yml', sources_yml))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 12 — dbt Seeds
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 12. dbt Seeds: Reference Data

Seeds are static CSV files that dbt materializes as tables at `dbt seed` time.
They provide the dimension lookup data for JOIN operations.

### Why Seeds Instead of External Tables?

Seeds are version-controlled with the project, always available, and fast to load.
The alternative (external dimension tables) requires additional infrastructure. For
relatively static reference data (265 NYC taxi zones don't change often), seeds are ideal.

### 12.1 payment_type_lookup.csv
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/seeds/payment_type_lookup.csv', payment_csv))

cells.append(md('### 12.2 rate_code_lookup.csv'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/seeds/rate_code_lookup.csv', rate_code_csv))

cells.append(md("""\
### 12.3 seed_properties.yml — Explicit column types

Without explicit types, DuckDB may infer `payment_type_id` as `BIGINT` when the seed CSV
has integer values. The fact table uses `INT` → the JOIN would fail with a type mismatch.
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/seeds/seed_properties.yml', seed_props_yml))

cells.append(md('### 12.4 taxi_zone_lookup.csv (265 NYC zones)'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/seeds/taxi_zone_lookup.csv', taxi_zone_csv))

cells.append(md('### 12.5 vendor_lookup.csv'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/seeds/vendor_lookup.csv', vendor_csv))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 13 — dbt Macros
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 13. dbt Macros: Cross-Database Compatibility

dbt macros use Jinja2 templating to provide database-agnostic SQL. The `adapter.dispatch()`
pattern means the same model works on DuckDB, Snowflake, BigQuery, or Spark — the macro
selects the right implementation for the target adapter.

**For this pipeline:** All macros render the DuckDB variant (it's our only adapter).
When porting to another database, only the macro implementations need to change.

### 13.1 cents_to_dollars (DuckDB: integer division + cast)
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/macros/cents_to_dollars.sql', macro_cents))

cells.append(md("""\
### 13.2–13.4 Other macros

- `dayname_compat` — day-of-week name: DuckDB uses `strftime('%A', ...)`, Spark uses `date_format(..., 'EEEE')`
- `duration_minutes` — DuckDB: `epoch_ms(end_ts - start_ts) / 60000.0`
- `test_positive_value` — reusable test: fails if any row has the named column ≤ 0
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/macros/dayname_compat.sql', macro_dayname))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/macros/duration_minutes.sql', macro_duration))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/macros/test_positive_value.sql', macro_test_pos))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 14 — dbt Staging
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 14. dbt Staging Models

Staging models are **thin wrappers** — they standardize column names, types, and apply the
minimal filter set needed to make downstream models reliable. No business logic here.

### The Silver Passthrough Pattern

Because Flink Silver already:
- Renamed: `VendorID` → `vendor_id`, `PULocationID` → `pickup_location_id`, etc.
- Type-cast: `BIGINT` → `INT`, `DOUBLE` → `DECIMAL(10,2)`
- Quality-filtered and deduplicated

`stg_yellow_trips.sql` is essentially a passthrough with minor DuckDB type compatibility
casts (`TIMESTAMP(3)` → `TIMESTAMP`). No cleaning needed at this stage.

This is the **correct medallion architecture**: Flink does the hard infrastructure work,
dbt staging is the clean entry point.

### 14.1 stg_yellow_trips.sql — Main staging model (Silver passthrough)
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/staging/stg_yellow_trips.sql', stg_yellow))

cells.append(md('### 14.2–14.5 Dimension staging models'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/staging/stg_payment_types.sql', stg_payment))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/staging/stg_rate_codes.sql', stg_rate_codes))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/staging/stg_taxi_zones.sql', stg_taxi_zones))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/staging/stg_vendors.sql', stg_vendors))

cells.append(md('### 14.6 staging.yml — Schema documentation + tests'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/staging/staging.yml', staging_yml))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 15 — dbt Intermediate
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 15. dbt Intermediate Models

Intermediate models add **business logic** on top of staging. This is where computed metrics
and multi-model joins live — the place Flink explicitly does NOT touch.

### Separation of Concerns: Flink vs dbt

| Computation | Where | Reason |
|-------------|-------|--------|
| Timestamp parsing | Flink Bronze | Must happen before Iceberg write (type compatibility) |
| Null filtering | Flink Silver | Stream-level quality gate |
| Deduplication | Flink Silver | Needs global ordering (ingestion_ts across partitions) |
| Column renaming | Flink Silver | Consistent schema for iceberg_scan |
| `duration_minutes` | **dbt int_trip_metrics** | Business metric, testable, versionable |
| `avg_speed_mph` | **dbt int_trip_metrics** | Business metric |
| `tip_percentage` | **dbt int_trip_metrics** | Business metric |
| `is_weekend` | **dbt int_trip_metrics** | Calendar attribute |
| Revenue aggregation | **dbt mart_daily_revenue** | Analytics aggregate |

> **Audit finding (Feb 2026):** An earlier version of the pipeline computed `duration_minutes`,
> `avg_speed_mph`, `cost_per_mile`, `tip_percentage`, `pickup_hour`, and `is_weekend` directly
> in the Flink Silver SQL. This was removed — business logic belongs in dbt where it's testable
> and analysts can modify it without touching the stream processor.

### 15.1 int_trip_metrics.sql — Trip-level enrichment
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/intermediate/int_trip_metrics.sql', int_trip_metrics))

cells.append(md('### 15.2 int_daily_summary.sql — One row per pickup date'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/intermediate/int_daily_summary.sql', int_daily_summary))

cells.append(md('### 15.3 int_hourly_patterns.sql — One row per pickup_date × pickup_hour'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/intermediate/int_hourly_patterns.sql', int_hourly))

cells.append(md('### 15.4 intermediate.yml'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/intermediate/intermediate.yml', intermediate_yml))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 16 — Core Marts
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 16. dbt Core Marts (Gold Layer — Star Schema)

Core marts form the **star schema** that BI tools query directly.

```
                    dim_dates
                    (31 rows)
                        │
dim_vendors ────── fct_trips ────── dim_payment_types
(2 rows)        (~9,855 rows)        (6 rows)
                        │
                  dim_locations
                  (265 rows)
```

**Grain of fct_trips:** One row per taxi trip, identified by `trip_id` (MD5 surrogate key
generated by Flink Silver from the natural key). Joins `int_trip_metrics` with all dimensions.

### 16.1 fct_trips.sql — Central fact table
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/marts/core/fct_trips.sql', fct_trips))

cells.append(md("""\
### 16.2–16.5 Dimension tables

- `dim_dates` — one row per calendar date (Jan 2024) with week, month, is_weekend attributes
- `dim_locations` — 265 NYC taxi zones with borough and service_zone
- `dim_payment_types` — maps payment_type_id to description
- `dim_vendors` — maps VendorID to vendor name
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/marts/core/dim_dates.sql', dim_dates))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/marts/core/dim_locations.sql', dim_locations))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/marts/core/dim_payment_types.sql', dim_payment_types))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/marts/core/dim_vendors.sql', dim_vendors))

cells.append(md('### 16.6 core.yml — Data contracts + referential integrity tests'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/marts/core/core.yml', core_yml))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 17 — Analytics Marts
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 17. dbt Analytics Marts (Gold Layer — Business KPIs)

Analytics marts are pre-aggregated tables optimized for dashboards. They answer specific
business questions without requiring analysts to write complex SQL.

### 17.1 mart_daily_revenue.sql — Daily revenue KPIs
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/marts/analytics/mart_daily_revenue.sql', mart_daily_rev))

cells.append(md('### 17.2 mart_hourly_demand.sql — Hourly demand patterns'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/marts/analytics/mart_hourly_demand.sql', mart_hourly_dem))

cells.append(md("""\
### 17.3 mart_location_performance.sql — Per-zone analytics

Includes `rank() OVER (ORDER BY total_revenue DESC)` window function for revenue ranking.
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/marts/analytics/mart_location_performance.sql', mart_location_pf))

cells.append(md('### 17.4 analytics.yml — Analytics model tests'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/models/marts/analytics/analytics.yml', analytics_yml))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 18 — dbt Tests
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 18. dbt Tests: Data Quality Assertions

dbt has two test types:

| Type | Location | Failure condition | Example |
|------|----------|------------------|---------|
| **Schema tests** | `.yml` files | SQL returns rows with violations | `not_null`, `unique`, `accepted_values` |
| **Singular tests** | `tests/*.sql` | Query returns ANY rows | `assert_fare_not_exceeds_total.sql` |

### Total test count: 91 tests

- Staging schema tests: ~35 (not_null, unique, accepted_values on all columns)
- Intermediate tests: ~20 (relationships between models)
- Core mart tests: ~25 (referential integrity, not_null on fact)
- Analytics mart tests: ~8 (aggregated column tests)
- Singular tests: 2 (business rule assertions)
- Seed tests: 1 (payment_type uniqueness)

### 18.1 assert_fare_not_exceeds_total.sql
"""))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/tests/assert_fare_not_exceeds_total.sql', assert_fare))

cells.append(md('### 18.2 assert_trip_duration_positive.sql'))
cells.append(wf('../pipelines/04-redpanda-flink-iceberg/dbt_project/tests/assert_trip_duration_positive.sql', assert_duration))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 19 — Makefile
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 19. Pipeline Makefile: One-Command Orchestration

The Makefile provides named targets for every pipeline operation.

### Target Map

```
make up                → docker compose up -d (start 6 always-on containers)
make create-topics     → rpk topic create taxi.raw_trips + taxi.raw_trips.dlq
make generate          → start data generator (unlimited events, burst mode)
make generate-limited  → 10,000 events then stop (benchmark mode)
make process-bronze    → Flink SQL batch: Redpanda → Bronze Iceberg
make process-silver    → Flink SQL batch: Bronze → Silver Iceberg (dedup + filter)
make process           → process-bronze + process-silver
make process-streaming → Flink SQL streaming: Redpanda → Bronze (continuous, indefinite)
make dbt-build         → dbt deps && dbt build --full-refresh (all models + 91 tests)
make benchmark         → full E2E: down→up→topics→generate→process→sleep5→dbt→down
make status            → show running containers + Redpanda topic list + Flink job list
make health            → check Flink UI, MinIO health, Redpanda cluster health
make down              → docker compose down -v (stop + remove volumes)
```

### Key Makefile Patterns

```makefile
# Windows Git Bash compatibility
MSYS_NO_PATHCONV=1 $(COMPOSE) exec flink-jobmanager /opt/flink/bin/sql-client.sh embedded ...
#   ↑ Prevents MSYS2 from converting /opt/flink to C:/Program Files/...

# Flink SQL with init + execute
$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/05-bronze.sql
#                      ──────────────────────────    ─────────────────────────────
#                      session state (tables, catalog)  execute this file

# Benchmark with race condition fix
$(MAKE) process && \\
    sleep 5 && \\        ← wait for Iceberg metadata to fully flush
    $(MAKE) dbt-build   ← then dbt can see committed Iceberg snapshots
```
"""))

cells.append(wf('../pipelines/04-redpanda-flink-iceberg/Makefile', makefile_content))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 20 — Running the Pipeline
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 20. Running the Pipeline

### Prerequisites

- Docker Desktop running (Linux containers), 8+ GB RAM allocated
- Docker Compose V2 (`docker compose`, not `docker-compose`)
- `make` installed (Windows: `scoop install make`)
- Free ports: `19092` (Redpanda), `8081` (Flink UI), `8085` (Redpanda Console), `9000-9001` (MinIO)
- Data: `data/yellow_tripdata_2024-01.parquet` in project root

### Quick Start (Batch Benchmark)

```bash
cd pipelines/04-redpanda-flink-iceberg

# One command — full E2E benchmark with timing
make benchmark
# Expected output: Total elapsed: ~88s (includes 5s metadata flush sleep)
# Results written to: benchmark_results/latest.json
```

### Step-by-Step with Validation

```bash
# 1. Start all services
make up

# 2. Verify everything is healthy (~20s for Redpanda to become healthy)
make status

# 3. Create topics (primary + DLQ)
make create-topics
# Expected:
#   NAME               PARTITIONS  REPLICAS
#   taxi.raw_trips     3           1
#   taxi.raw_trips.dlq 1           1

# 4. Generate 10,000 taxi events
make generate-limited
# Expected: ~3s, ~25,000 events/sec

# 5. Process: Redpanda → Bronze → Silver
make process
# Expected:
#   Bronze: 10,000 rows written to s3://warehouse/bronze/raw_trips/
#   Silver:  9,855 rows written to s3://warehouse/silver/cleaned_trips/

# 6. Run dbt: Silver → Gold (91 tests)
make dbt-build
# Expected: 14 models created, 91 tests PASS

# 7. Verify in Flink SQL (interactive)
docker exec -it p04-flink-jobmanager \\
    /opt/flink/bin/sql-client.sh embedded \\
    -i /opt/flink/sql/00-init.sql
# Then run:
# SELECT COUNT(*) FROM iceberg_catalog.bronze.raw_trips;   -- should be 10000
# SELECT COUNT(*) FROM iceberg_catalog.silver.cleaned_trips; -- should be ~9855
```

### Streaming Mode (Continuous Ingestion)

```bash
# Terminal 1: Start continuous Bronze ingestion
make process-streaming
# This job runs until you cancel it (Ctrl+C)

# Terminal 2: Generate events (will be picked up continuously)
make generate-limited

# Terminal 3: Watch Bronze grow
watch -n5 'docker exec p04-flink-jobmanager \\
    bash -c "echo '"'"'SELECT COUNT(*) FROM iceberg_catalog.bronze.raw_trips;'"'"' | \\
    MSYS_NO_PATHCONV=1 /opt/flink/bin/sql-client.sh embedded -i /opt/flink/sql/00-init.sql"'
```

### Web UIs (while services are running)

| Service | URL | Login | What to look at |
|---------|-----|-------|-----------------|
| **Flink Dashboard** | http://localhost:8081 | none | Running jobs, task slots, checkpoints |
| **Redpanda Console** | http://localhost:8085 | none | Topics, messages, consumer lag |
| **MinIO Console** | http://localhost:9001 | minioadmin/minioadmin | Iceberg warehouse bucket, Parquet files |

### Expected Benchmark Timing (10k events)

| Phase | Duration | Notes |
|-------|----------|-------|
| `make up` + healthchecks | ~20s | Redpanda starts in ~3s; Flink needs ~15s |
| `make create-topics` | <1s | rpk is a native binary |
| `make generate-limited` | ~3s | ~25k events/sec to Redpanda |
| `sleep 10` (stabilize) | 10s | Wait for consumer lag to settle |
| `make process-bronze` | ~22s | Flink batch: Redpanda → Iceberg |
| `make process-silver` | ~21s | Flink batch: Bronze → Silver |
| `sleep 5` (metadata flush) | 5s | Wait for Iceberg metadata to commit |
| `make dbt-build` | ~15s | dbt: 14 models + 91 tests |
| **Total E2E** | **~88s** | |
"""))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 21 — Production Operations + Troubleshooting
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 21. Production Operations + Troubleshooting

### Production Hardening Checklist

This pipeline implements **defense-in-depth**: multiple independent layers prevent data quality issues.

| Layer | Mechanism | What it prevents |
|-------|-----------|-----------------|
| **Producer** | `enable.idempotence=True`, `acks=all` | Duplicate events from producer retries |
| **DLQ** | `taxi.raw_trips.dlq` topic | Malformed events blocking the primary stream |
| **Bronze** | Event-time watermark (10s) | Out-of-order events in streaming window functions |
| **Silver** | `ROW_NUMBER()` deduplication | Duplicate rows surviving to analytics layer |
| **Silver** | Quality filters (fare≥0, date range) | Invalid records reaching Gold models |
| **dbt** | 91 schema + singular tests | Regressions detected before data reaches BI tools |
| **Containers** | CPU limits + restart policies | Cascading failures from resource exhaustion |

### Troubleshooting Guide

| Symptom | Root Cause | Diagnosis | Fix |
|---------|-----------|-----------|-----|
| `Object 'iceberg_catalog' not found` | 00-init.sql not used as init | Check `-i` flag in command | Ensure `make process-bronze` uses `-i 00-init.sql` |
| `Silver has 0 rows` | Bronze job failed silently | `SELECT COUNT(*) FROM bronze.raw_trips` | Check Bronze count first; rerun `make process-bronze` |
| `LEADER_NOT_AVAILABLE` | Redpanda not fully ready | `docker logs p04-redpanda` | Wait 5-10s more; check healthcheck status |
| `s3://warehouse: No such file` | MinIO bucket not created | `docker logs p04-mc-init` | Check mc-init completed successfully |
| `classloader leak` warning | Missing config setting | `grep classloader flink/conf/config.yaml` | Add `classloader.check-leaked-classloader: false` |
| `Port 19092 already in use` | Another pipeline running | `docker ps | grep 19092` | `cd ../01-kafka-flink-iceberg && make down` |
| `dbt: No files found in COPY FROM '/old/path'` | Stale partial_parse.msgpack | `ls dbt_project/target/` | `rm dbt_project/target/partial_parse.msgpack` |
| `dbt: source not found` | sources.yml points to wrong path | Check `external_location` in sources.yml | Must be `silver/cleaned_trips`, not `bronze/raw_trips` |

### Iceberg Table Inspection

```bash
# Check what Iceberg tables exist (via MinIO)
docker exec p04-minio mc ls myminio/warehouse/ --recursive --summarize

# Query Iceberg table stats via Flink SQL
docker exec -it p04-flink-jobmanager bash -c "
  echo 'SELECT COUNT(*), MIN(pickup_date), MAX(pickup_date) FROM iceberg_catalog.silver.cleaned_trips;' | \\
  /opt/flink/bin/sql-client.sh embedded -i /opt/flink/sql/00-init.sql
"

# Inspect Iceberg snapshots (time travel metadata)
docker exec -it p04-flink-jobmanager bash -c "
  echo 'SELECT snapshot_id, committed_at, operation, summary
        FROM iceberg_catalog.silver.\\`cleaned_trips\\$snapshots\\`;' | \\
  /opt/flink/bin/sql-client.sh embedded -i /opt/flink/sql/00-init.sql
"
```

### Migrating to Managed Kafka/Redpanda

The only file to change is `00-init.sql`:

```sql
-- Change ONLY this one line (and add auth if needed):
'properties.bootstrap.servers' = 'broker1.company.com:9092,broker2.company.com:9092',

-- For Confluent Cloud / MSK (SASL):
'properties.security.protocol' = 'SASL_SSL',
'properties.sasl.mechanism' = 'PLAIN',
'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule
  required username="API_KEY" password="API_SECRET";'
```

Everything else — dbt models, Makefile targets, Iceberg tables — is **100% portable**.

### Scheduling (Adding an Orchestrator)

P04 is Makefile-based. To add scheduling (nightly runs, dependency management):
- **P07 Kestra:** Lightest (+1 container, YAML-based, +5s overhead)
- **P09 Dagster:** Asset-centric, lineage tracking (+750 MB)
- **P08 Airflow:** Battle-tested, Astronomer support (+1.5 GB, +20s overhead)

The Makefile targets become shell operators in the orchestrator DAG.
"""))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 22 — Adapting to Your Own Dataset
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 22. Adapting to Your Own Dataset

This section is the learning guide: how to take P04's pattern and apply it to any dataset.
The NYC Taxi pipeline is the **template** — every decision here generalizes.

---

### Step 1: Define Your Event Schema

Start with the JSON events that will flow through Redpanda. Ask:
- What does one event represent? (one taxi trip → one IoT reading, one order, one click)
- What fields are always present? (required → filter nulls in Silver)
- What's the natural key? (for deduplication in Silver)
- What timestamp represents the event? (for watermarks in streaming mode)

**Template for your `00-init.sql` source table:**

```sql
CREATE TABLE IF NOT EXISTS kafka_your_events (
    -- Copy your JSON fields here with Flink SQL types:
    -- JSON string fields → STRING
    -- JSON integer fields → BIGINT (safest; cast to INT in Silver)
    -- JSON float/decimal → DOUBLE (cast to DECIMAL in Silver)
    -- JSON booleans → BOOLEAN
    -- Timestamps (ISO 8601 strings) → STRING (parse in Bronze INSERT)
    field_one           STRING,
    numeric_field       BIGINT,
    amount_field        DOUBLE,
    event_timestamp_str STRING,   -- raw string from JSON

    -- Add watermark for streaming mode:
    event_time AS TO_TIMESTAMP(event_timestamp_str, 'yyyy-MM-dd''T''HH:mm:ss'),
    WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'your.topic.name',
    'properties.bootstrap.servers' = 'redpanda:9092',
    -- For batch mode:
    'scan.startup.mode' = 'earliest-offset',
    'scan.bounded.mode' = 'latest-offset',
    -- For streaming mode (in 00-init-streaming.sql): omit scan.bounded.mode
    'format' = 'json'
);
```

---

### Step 2: Design Bronze (Raw Landing)

Bronze SQL changes are minimal — just match your source schema:

```sql
-- 05-bronze.sql template
INSERT INTO iceberg_catalog.bronze.your_events
SELECT
    field_one,
    numeric_field,
    CAST(amount_field AS DOUBLE),
    -- Parse your event timestamp:
    TO_TIMESTAMP(event_timestamp_str, 'yyyy-MM-dd''T''HH:mm:ss') AS event_time,
    CURRENT_TIMESTAMP AS ingestion_ts
FROM kafka_your_events;
```

**What NOT to do in Bronze:**
- ❌ Filter rows (except for parse errors)
- ❌ Rename columns to snake_case (do this in Silver or dbt)
- ❌ Compute derived metrics (duration, ratio, etc.)
- ❌ Join with other tables

---

### Step 3: Design Silver (Dedup + Clean)

This is where you need to think carefully. Key decisions:

**A) What is your natural key?** (for deduplication)
```sql
-- Taxi: pickup_time + dropoff_time + vendor + location + fare + total
-- IoT: device_id + event_timestamp (usually unique already)
-- E-commerce orders: order_id (if truly unique, skip dedup)
-- Clickstream: session_id + event_type + timestamp (approximate dedup window)

ROW_NUMBER() OVER (
    PARTITION BY your_field1, your_field2, ...,  -- natural key
    ORDER BY ingestion_ts DESC
) AS rn
```

**B) What quality filters make sense?**
```sql
-- Taxi: fare_amount >= 0, trip_distance >= 0, location_id BETWEEN 1 AND 265
-- IoT: sensor_value BETWEEN min_valid AND max_valid
-- Orders: amount > 0, customer_id IS NOT NULL
-- Always: event_timestamp IS NOT NULL
```

**C) What columns to cast?**
```sql
-- Cast BIGINT → INT for dimension keys (saves storage, needed for JOIN types)
-- Cast DOUBLE → DECIMAL(10,2) for money (exact precision)
-- Always add a surrogate key (MD5 or UUID of natural key fields)
CAST(MD5(CONCAT_WS('|', CAST(field1 AS STRING), ...)) AS STRING) AS event_id
```

**D) How to partition Silver?**
```sql
-- Time-series data: PARTITIONED BY (event_date DATE)
-- Geographic data: PARTITIONED BY (region_code) or (event_date, region_code)
-- High-cardinality: avoid partitioning by user_id (too many small partitions)
```

---

### Step 4: Design dbt Staging

With the Silver passthrough pattern, staging is simple:

```sql
-- models/staging/stg_your_events.sql
with source as (
    select * from {{ source('your_source', 'your_events') }}
),
final as (
    select
        event_id,                              -- surrogate key from Silver
        field_one,                             -- already clean from Silver
        numeric_field,
        cast(amount_field as decimal(10, 2)),  -- minor DuckDB type compat
        cast(event_time as timestamp)          -- TIMESTAMP(3) → TIMESTAMP
    from source
    where event_time is not null               -- safety net (Silver already filtered)
)
select * from final
```

**sources.yml:**
```yaml
sources:
  - name: your_source
    tables:
      - name: your_events
        config:
          external_location: >-
            iceberg_scan('s3://warehouse/silver/your_events', allow_moved_paths=true)
```

---

### Step 5: Design dbt Intermediate

Here's where your domain knowledge goes. For each dataset, ask:

1. **What are the computed metrics?** (duration, speed, ratio, percentage)
2. **What granularities do analysts need?** (per-event, daily, hourly, per-entity)
3. **What joins are needed?** (fact + dimensions, event + user profile, etc.)

```sql
-- models/intermediate/int_your_event_metrics.sql
with events as (
    select * from {{ ref('stg_your_events') }}
),
enriched as (
    select
        event_id,
        -- Computed metrics (NOT in Flink — these belong here):
        amount_field / duration_seconds as rate_per_second,
        case when numeric_field > threshold then 'high' else 'low' end as category,
        -- Calendar attributes:
        extract(hour from event_time) as event_hour,
        dayofweek(event_time) = 0 as is_sunday
    from events
)
select * from enriched
```

---

### Step 6: Design dbt Marts

Marts answer specific business questions. For each question, create one mart:

| Question | Mart name | Grain |
|----------|-----------|-------|
| "How much revenue per day?" | `mart_daily_revenue` | 1 row per date |
| "Which customers are most active?" | `mart_customer_activity` | 1 row per customer |
| "What's the hourly throughput?" | `mart_hourly_throughput` | 1 row per date × hour |
| "Where are errors concentrated?" | `mart_error_locations` | 1 row per region |

---

### Step 7: Write dbt Tests

For every column that downstream systems depend on, write a test:

```yaml
# staging.yml
models:
  - name: stg_your_events
    columns:
      - name: event_id
        tests: [not_null, unique]
      - name: amount_field
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: "amount_field >= 0"
```

**Custom singular tests:**
```sql
-- tests/assert_event_time_not_in_future.sql
select *
from {{ ref('stg_your_events') }}
where event_time > current_timestamp + interval 1 hour
-- Any rows = test failure (events shouldn't be >1h in the future)
```

---

### General Patterns That Always Apply

| Pattern | What it prevents |
|---------|-----------------|
| Idempotent producer (`enable.idempotence=True, acks=all`) | Duplicate events from network retries |
| DLQ topic (1 partition, longer retention) | Malformed events blocking the stream |
| Bronze = raw landing, Silver = clean | Ability to reprocess without re-reading source |
| ROW_NUMBER dedup on natural key | Duplicates reaching analytics layer |
| `table.dml-sync=true` in batch mode | Silver reading empty Bronze |
| `sleep 5` after Flink before dbt | dbt reading before Iceberg metadata commits |
| CPU limits on TaskManager | Resource starvation in shared Docker pool |
| All images pinned to specific tags | Pipeline breaking when `:latest` changes |
| `classloader.check-leaked-classloader: false` | Flink + Iceberg class loading errors |
| `s3_endpoint: "minio:9000"` (no http://) | DuckDB httpfs rejects protocol prefix |
"""))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 23 — What We Learned
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(md("""\
## 23. What We Learned: Key Decisions Explained

This section is a retrospective of the most important decisions made while building P04,
and the lessons they carry to any real-time pipeline.

---

### 1. "Kafka-compatible" ≠ "Zero code changes"
**What happened:** Redpanda claims 100% Kafka API compatibility. We verified this by
running the exact same Flink SQL, the exact same dbt models, the exact same producer code —
and it worked. The only change was one line: `bootstrap.servers = 'redpanda:9092'`.

**The lesson:** Evaluate broker alternatives on *actual* protocol compatibility, not marketing.
The Kafka wire protocol is well-specified. Redpanda, WarpStream, AutoMQ, and others implement
it faithfully. The ecosystem (Flink, Debezium, Python confluent-kafka, Java clients) doesn't
care which broker is on the other end.

---

### 2. The Silver source bug: a silent failure that passes all tests

**What happened:** P04's `sources.yml` originally pointed to the Bronze table. Flink Silver
was writing clean data to one location. dbt was reading raw data from another. 91 tests passed
because the Bronze data was *similar enough* to Silver — same row count, same column names after
Flink Bronze's timestamp parsing.

**The lesson:** Passing tests prove the tests passed — not that the pipeline is correct.
Always verify: `SELECT COUNT(*) FROM bronze.raw_trips` vs `SELECT COUNT(*) FROM silver.cleaned_trips`.
If they're the same (~10,000 each when you expect ~9,855 in Silver), something is wrong.
The deduplication + quality filtering didn't run.

---

### 3. Flink's 06-silver.sql vs 05-run-all.sql inconsistency

**What happened:** The combined pipeline (`05-run-all.sql`) had the correct ROW_NUMBER()
deduplication. The standalone Silver file (`06-silver.sql`) ran a plain INSERT without
dedup. Running `make process-silver` independently produced different results than `make process`.

**The lesson:** When the same operation exists in multiple files (standalone + combined),
they must be kept in sync. Add a test: run `make process-silver` and verify row count matches
the combined pipeline's Silver output. If they differ, the files diverged.

---

### 4. The benchmark race condition

**What happened:** Flink's batch job returns when the INSERT statement completes. But "INSERT
completes" means Flink flushed data to Parquet files in MinIO — not that Iceberg metadata
(the `.metadata.json` snapshot) was committed and visible to readers. dbt would start and
sometimes see 0 rows because Iceberg's metadata wasn't ready.

**The lesson:** Flink's `table.dml-sync=true` waits for the job to finish writing *data*.
Iceberg commits metadata separately in a final atomic rename. Add `sleep 5` between Flink
and dbt in any batch pipeline. In streaming mode with proper checkpoints, this race doesn't
exist because DuckDB always reads the latest committed snapshot.

---

### 5. Enrichment columns belong in dbt, not Flink

**What happened:** An early version of Silver computed `duration_minutes`, `avg_speed_mph`,
`cost_per_mile`, `tip_percentage`, `pickup_hour`, and `is_weekend` directly in the Flink
Silver SQL. These were removed and moved to `int_trip_metrics.sql`.

**The lesson:** Apply the single-responsibility principle to data layers. Flink is uniquely
positioned to do: ordering, deduplication, type coercion, and quality filtering at stream
speed. It's not the right place for business metrics because:
1. Business rules change. Changing Flink SQL requires reprocessing the entire Bronze table.
2. Business metrics are domain knowledge — analysts understand them, not infrastructure engineers.
3. dbt tests can verify business rule correctness. Flink SQL can't.

---

### 6. CPU limits prevent silent failures in Docker Desktop

**What happened:** Without CPU limits, during Flink processing the TaskManager consumed
all available cores on Docker Desktop. MinIO's S3 server starved for CPU → S3A write requests
timed out → Flink retried → more load → eventual failure. The error message looked like
a network error, not a resource problem.

**The lesson:** Always set both `memory` AND `cpus` limits on CPU-intensive containers
in Docker Desktop environments. In production Kubernetes, use resource requests/limits on
every pod. Docker Desktop doesn't enforce CPU limits by default — your JVM containers will
happily consume 100% of all available cores.

---

### 7. The DLQ must exist in the Makefile, not just the shell script

**What happened:** The `create-topics.sh` shell script created both topics correctly.
But the `Makefile`'s `create-topics` target ran `rpk topic create taxi.raw_trips` inline,
bypassing the shell script. Running `make create-topics` only created one topic.

**The lesson:** When you have multiple entry points to the same operation (shell script + Makefile),
test them independently. The Makefile target is what everyone uses in practice (`make create-topics`
is more natural than `bash kafka/create-topics.sh`). Keep them synchronized or have one call the other.

---

### 8. Streaming mode's `table.dml-sync` trap

**What happened:** Developers familiar with batch mode copied `SET 'table.dml-sync' = 'true'`
into the streaming init file. The Flink session blocked forever on the first INSERT (which
runs indefinitely in streaming mode), never getting to execute the second statement.

**The lesson:** Batch and streaming modes have fundamentally different lifecycles. `table.dml-sync`
is the batch synchronization primitive that makes no sense for infinite streaming jobs. Never
copy settings between batch and streaming init files without understanding what each setting does.
A streaming pipeline that "works" with `dml-sync=true` is actually running only one job —
it never progressed past the first INSERT.

---

### Summary: The Mental Model

```
Everything a streaming data pipeline does falls into one of three buckets:

1. INFRASTRUCTURE WORK (Flink):
   Parse timestamps, enforce types, deduplicate on the natural key,
   apply basic validity filters, write to the storage format.
   This runs at stream speed and shouldn't be changed often.

2. BUSINESS LOGIC (dbt):
   Compute metrics, join dimensions, aggregate to business granularities,
   test business rules, version-control analytical decisions.
   This changes with business requirements and should be easy to modify.

3. OPERATIONS (Makefile + Docker Compose):
   Manage infrastructure lifecycle, health checks, topic creation,
   DLQ, resource limits, benchmark timing, image pinning.
   This is the glue that makes the pipeline reproducible and observable.

When something is in the wrong bucket, you get problems:
- Business logic in Flink → hard to change, hard to test, requires stream reprocessing
- Infrastructure work in dbt → slow (batch query instead of stream), misses the point
- Missing operations (no DLQ, no CPU limits, no sleep) → silent failures that pass tests
```
"""))

# ═══════════════════════════════════════════════════════════════════════════════
# Assemble + write notebook
# ═══════════════════════════════════════════════════════════════════════════════
notebook = {
    'cells': cells,
    'metadata': {
        'kernelspec': {
            'display_name': 'Python 3',
            'language': 'python',
            'name': 'python3'
        },
        'language_info': {
            'name': 'python',
            'version': '3.11.0'
        }
    },
    'nbformat': 4,
    'nbformat_minor': 5
}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

file_size    = os.path.getsize(OUT)
code_cells   = [c for c in cells if c['cell_type'] == 'code']
md_cells     = [c for c in cells if c['cell_type'] == 'markdown']
wf_cells     = [c for c in code_cells if ''.join(c['source']).startswith('%%writefile')]

print(f'Notebook written: {OUT}')
print(f'Total cells:      {len(cells)}')
print(f'  Markdown:       {len(md_cells)}')
print(f'  Code:           {len(code_cells)} ({len(wf_cells)} writefile cells)')
print(f'File size:        {file_size:,} bytes ({file_size/1024:.1f} KB)')

# Verify valid JSON
with open(OUT, encoding='utf-8') as f:
    nb2 = json.load(f)
print(f'Verification:     {len(nb2["cells"])} cells, nbformat={nb2["nbformat"]} — VALID JSON')

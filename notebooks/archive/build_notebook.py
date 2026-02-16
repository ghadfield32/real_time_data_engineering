"""Build the complete Pipeline 01 walkthrough notebook with %%writefile cells.

Reads all actual pipeline files from disk and constructs a Jupyter notebook
that can recreate the entire pipeline from scratch.
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P01 = os.path.join(BASE, "pipelines", "01-kafka-flink-iceberg")
SHARED = os.path.join(BASE, "shared")

cells = []


def md(source):
    """Add a markdown cell."""
    lines = source.split("\n")
    src = [line + "\n" for line in lines[:-1]]
    if lines[-1]:
        src.append(lines[-1])
    elif src:
        pass  # trailing empty line already handled
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": src
    })


def code(source):
    """Add a code cell."""
    lines = source.split("\n")
    src = [line + "\n" for line in lines[:-1]]
    if lines[-1]:
        src.append(lines[-1])
    cells.append({
        "cell_type": "code",
        "metadata": {},
        "source": src,
        "outputs": [],
        "execution_count": None
    })


def read_file(path):
    """Read file content, stripping trailing newline."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return content.rstrip("\n")


def writefile(relative_path, file_path):
    """Create a %%writefile cell reading content from disk."""
    content = read_file(file_path)
    code(f"%%writefile {relative_path}\n{content}")


def bash(cmd, description=""):
    """Create a bash cell (for running commands)."""
    if description:
        code(f"%%bash\n# {description}\n{cmd}")
    else:
        code(f"%%bash\n{cmd}")


# =============================================================================
# BUILD THE NOTEBOOK
# =============================================================================

# ── SECTION 0: Title & Table of Contents ────────────────────────────────────
md("""# Pipeline 01: Complete Production Walkthrough
## Kafka → Flink → Iceberg → dbt

**Pipeline:** P01 - Kafka + Flink + Iceberg (Industry Standard Stack)
**Status:** Production-Ready (91/91 dbt tests passing)
**Performance:** ~107s E2E, 7.7GB memory footprint
**Stack:** Netflix/Apple/Uber-grade architecture

---

### What This Notebook Does

Every code cell uses `%%writefile` to create the **exact production files** on disk.
After running all cells top-to-bottom, you will have a complete, working pipeline
that you can start with `make up && make benchmark`.

### Table of Contents

| # | Section | What You'll Build |
|---|---------|-------------------|
| 1 | Architecture Overview | Understanding the data flow |
| 2 | Shared Infrastructure | Dockerfiles, data generator, schemas |
| 3 | Docker Compose | 7-service container orchestration |
| 4 | Kafka Layer | Topic creation, event ingestion |
| 5 | Flink Configuration | Cluster config, S3/MinIO connectivity |
| 6 | Flink SQL - Init & Sources | Catalog + Kafka connector setup |
| 7 | Flink SQL - Bronze Layer | Kafka → Iceberg raw ingestion |
| 8 | Flink SQL - Silver Layer | Data quality + enrichment |
| 9 | Flink SQL - Combined Pipeline | Single-file Bronze + Silver |
| 10 | dbt Project Configuration | Project, profiles, packages |
| 11 | dbt Seeds | Reference data (zones, payment types, rate codes) |
| 12 | dbt Macros | Cross-database compatibility helpers |
| 13 | dbt Staging Models | Light transforms from Iceberg Silver |
| 14 | dbt Intermediate Models | Trip metrics, daily & hourly aggregations |
| 15 | dbt Core Marts | Fact & dimension tables (Gold layer) |
| 16 | dbt Analytics Marts | Revenue, demand, location performance |
| 17 | dbt Tests | Data quality assertions |
| 18 | Pipeline Makefile | One-command orchestration |
| 19 | Airflow DAGs | Production scheduling & maintenance |
| 20 | Running the Pipeline | Step-by-step execution guide |
| 21 | Production Operations | Monitoring, alerting, scaling |

---""")


# ── SECTION 1: Architecture Overview ────────────────────────────────────────
md("""## 1. Architecture Overview

### Data Plane vs Control Plane

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DATA PLANE (Always-On Services)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Parquet   →  [Data Generator]  →  Kafka Topic  →  Flink Jobs     │
│  (Source)     (burst producer)     (taxi.raw_trips)  │    │        │
│                                                      │    │        │
│                                          ┌───────────┘    │        │
│                                          ▼                ▼        │
│                                   Iceberg Bronze    Iceberg Silver  │
│                                   (raw_trips)      (cleaned_trips) │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   CONTROL PLANE (Scheduled by Airflow)              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Airflow DAG (every 10 min):                                       │
│    ├─ Health Check (Flink cluster status)                          │
│    ├─ dbt Build (Silver → Gold: 15 models via DuckDB+Iceberg)     │
│    └─ dbt Test (91 data quality assertions)                        │
│                                                                     │
│  Maintenance DAG (daily 2 AM):                                     │
│    ├─ Iceberg Compaction (merge small files)                       │
│    ├─ Snapshot Expiration (cleanup old metadata)                   │
│    └─ Orphan File Cleanup (reclaim storage)                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Owns | Technology | Runs |
|-------|------|------------|------|
| **Kafka** | Event buffering, ordering, replay, fan-out | Apache Kafka (KRaft) | Always-on |
| **Flink** | Real-time transforms, validation, enrichment | Apache Flink 1.20 | Long-running |
| **Iceberg** | ACID tables, time travel, schema evolution | Apache Iceberg 1.7 | Storage layer |
| **MinIO** | S3-compatible object storage backend | MinIO | Always-on |
| **dbt** | Dimensional modeling, KPIs, testing, docs | dbt-core + DuckDB | Scheduled |
| **Airflow** | Scheduling, retries, alerts, dependencies | Apache Airflow | Control plane |

### Medallion Architecture

```
Bronze (Raw)          Silver (Cleaned)           Gold (Analytics)
─────────────        ─────────────────          ─────────────────
• Kafka events       • snake_case columns       • fct_trips
• Parsed timestamps  • Type casting             • dim_locations
• No filtering       • Quality filters          • dim_dates
• Ingestion metadata • Surrogate keys           • mart_daily_revenue
                     • Derived columns          • mart_hourly_demand
                     • Deduplication            • mart_location_performance
```

### Data Flow Volumes (10k events)

```
Parquet Source:  2,964,624 rows (full month)
     ↓ (sample 10k)
Kafka Topic:     10,000 events  (31,250 evt/s ingestion)
     ↓
Bronze Table:    10,000 rows    (raw, all events)
     ↓ (quality filters ~1.5% rejection)
Silver Table:    ~9,855 rows    (cleaned, enriched)
     ↓ (dbt transforms)
Gold Tables:
  • fct_trips:                ~9,855 rows (1 per trip)
  • dim_locations:              265 rows  (taxi zones)
  • dim_dates:                   31 rows  (Jan 2024)
  • mart_daily_revenue:          31 rows  (1 per day)
  • mart_hourly_demand:          48 rows  (24h × weekday/weekend)
  • mart_location_performance:  ~260 rows (1 per zone)
```

---""")


# ── SECTION 2: Shared Infrastructure ────────────────────────────────────────
md("""## 2. Shared Infrastructure

These files live in `shared/` and are reused across multiple pipelines.
We create them first since Docker Compose references them.

### 2.1 Flink Dockerfile

Custom Flink image with **7 JARs** pre-installed:
- Kafka SQL connector (for reading Kafka topics as Flink tables)
- Iceberg Flink runtime (for writing to Iceberg tables)
- Iceberg AWS bundle (for S3FileIO with MinIO)
- Hadoop client API + runtime (for Iceberg Hadoop catalog)
- Hadoop AWS (for S3A filesystem)
- AWS SDK bundle (required by hadoop-aws)""")

writefile(
    "../shared/docker/flink.Dockerfile",
    os.path.join(SHARED, "docker", "flink.Dockerfile")
)

md("""### 2.2 dbt Dockerfile

Slim Python image with dbt-core and dbt-duckdb for reading Iceberg tables via DuckDB's `iceberg_scan()` function.""")

writefile(
    "../shared/docker/dbt.Dockerfile",
    os.path.join(SHARED, "docker", "dbt.Dockerfile")
)

md("""### 2.3 Data Generator

Reads NYC Yellow Taxi parquet data and produces JSON events to Kafka.
Three modes: `burst` (benchmarking), `realtime` (simulated pacing), `batch` (chunked).

**Dependencies:**""")

writefile(
    "../shared/data-generator/requirements.txt",
    os.path.join(SHARED, "data-generator", "requirements.txt")
)

md("**Generator script** (~210 lines, production-grade with metrics output):")

writefile(
    "../shared/data-generator/generator.py",
    os.path.join(SHARED, "data-generator", "generator.py")
)

md("""### 2.4 Event Schema (JSON Schema)

Defines the contract for taxi trip events. Field names match the raw NYC TLC parquet source.""")

writefile(
    "../shared/schemas/taxi_trip.json",
    os.path.join(SHARED, "schemas", "taxi_trip.json")
)


# ── SECTION 3: Docker Compose ───────────────────────────────────────────────
md("""## 3. Docker Compose: Container Orchestration

This defines all 7 services (+ 2 optional profiles for generator and dbt):

| Service | Image | Purpose | Port |
|---------|-------|---------|------|
| `kafka` | apache/kafka:latest | Event backbone (KRaft, no Zookeeper) | 9092 |
| `schema-registry` | cp-schema-registry:7.6.0 | Avro schema management | 8081 |
| `minio` | minio/minio:latest | S3-compatible object storage | 9000/9001 |
| `mc-init` | minio/mc:latest | Creates warehouse + checkpoints buckets | - |
| `flink-jobmanager` | Custom (flink.Dockerfile) | Flink cluster coordinator | 8081 |
| `flink-taskmanager` | Custom (flink.Dockerfile) | Flink worker (4 task slots) | - |
| `data-generator` | python:3.12-slim (profile) | Parquet → Kafka producer | - |
| `dbt` | Custom (dbt.Dockerfile, profile) | Silver → Gold transforms | - |

**Key design patterns:**
- Health checks on all critical services (Kafka, Schema Registry, MinIO)
- `depends_on` with `condition: service_healthy` for proper startup ordering
- Docker profiles for on-demand services (`generator`, `dbt`)
- Named network (`p01-pipeline-net`) for service discovery
- Named volumes for persistent storage (`minio-data`, `flink-checkpoints`)""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/docker-compose.yml",
    os.path.join(P01, "docker-compose.yml")
)


# ── SECTION 4: Kafka Layer ──────────────────────────────────────────────────
md("""## 4. Kafka Layer: Event Ingestion

### What Kafka Provides
- **Durable event buffering** with configurable retention (7 days default)
- **Ordering guarantee** per partition (3 partitions for parallelism)
- **Replay capability** for reprocessing and backfills
- **Consumer lag** as a monitoring signal

### Topic Design
- **Topic:** `taxi.raw_trips`
- **Partitions:** 3 (matches Flink parallelism)
- **Key:** `PULocationID` (pickup location for co-located processing)
- **Retention:** 24 hours (configurable)
- **Cleanup policy:** delete (not compacted)

### Topic Creation Script""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/kafka/create-topics.sh",
    os.path.join(P01, "kafka", "create-topics.sh")
)


# ── SECTION 5: Flink Configuration ─────────────────────────────────────────
md("""## 5. Flink Configuration

### 5.1 Hadoop core-site.xml

**Critical for Flink → MinIO connectivity.** Without this, Flink cannot write Iceberg tables to S3-compatible storage.

Key settings:
- `fs.s3a.endpoint` → MinIO URL
- `fs.s3a.path.style.access` → `true` (required for MinIO, not real S3)
- `fs.s3a.impl` → S3AFileSystem (Hadoop's S3 adapter)""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/flink/conf/core-site.xml",
    os.path.join(P01, "flink", "conf", "core-site.xml")
)

md("""### 5.2 Flink Cluster Configuration

Controls memory allocation, parallelism, checkpointing, and SQL behavior.

Key settings:
- **Memory:** JobManager 1600m, TaskManager 2048m
- **Parallelism:** 2 default, 4 task slots
- **Checkpointing:** EXACTLY_ONCE, 30s interval, 5min timeout
- **Classloader:** `check-leaked-classloader: false` (required for Iceberg batch DML sync)
- **SQL:** `table.exec.sink.not-null-enforcer: DROP` (drop nulls instead of failing)""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/flink/conf/flink-conf.yaml",
    os.path.join(P01, "flink", "conf", "flink-conf.yaml")
)


# ── SECTION 6: Flink SQL - Init & Sources ───────────────────────────────────
md("""## 6. Flink SQL: Session Initialization

### How Flink SQL Files Work Together

```
sql-client.sh embedded -i 00-init.sql -f 05-bronze.sql
                        ↑               ↑
                        │               └── Execute: the SQL to run
                        └── Init: sets up catalog + Kafka source table
```

The `-i` flag runs `00-init.sql` first to establish the session context (Kafka source table + Iceberg catalog).
Then `-f` runs the target SQL file within that session.

### 6.1 Session Init (00-init.sql)

This file is the **foundation** for all Flink SQL jobs. It:
1. Sets batch execution mode (process all data, then stop)
2. Enables DML sync (wait for INSERT to complete)
3. Creates the Kafka source table (maps to `taxi.raw_trips` topic)
4. Creates the Iceberg catalog (Hadoop-based, MinIO backend)""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/flink/sql/00-init.sql",
    os.path.join(P01, "flink", "sql", "00-init.sql")
)

md("""### 6.2 Kafka Source Table (Reference)

This is the standalone version of the Kafka table definition. Included in `00-init.sql` but useful as documentation.""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/flink/sql/01-create-kafka-source.sql",
    os.path.join(P01, "flink", "sql", "01-create-kafka-source.sql")
)

md("""### 6.3 Iceberg Catalog (Reference)

Standalone catalog creation. Also included in `00-init.sql`.

Key properties:
- `catalog-type: hadoop` → Uses filesystem-based catalog metadata
- `warehouse: s3a://warehouse/` → MinIO bucket for all Iceberg data
- `io-impl: S3FileIO` → Iceberg's own S3 implementation""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/flink/sql/02-create-iceberg-catalog.sql",
    os.path.join(P01, "flink", "sql", "02-create-iceberg-catalog.sql")
)


# ── SECTION 7: Flink SQL - Bronze Layer ─────────────────────────────────────
md("""## 7. Flink SQL: Bronze Layer (Kafka → Iceberg)

### What Bronze Does
- Preserves **all** original fields from Kafka events
- Parses ISO 8601 timestamp strings → `TIMESTAMP(3)` type
- Adds `ingestion_ts` metadata column (when the event was processed)
- **No filtering**, no validation, no business logic
- Writes ACID Iceberg tables to MinIO (`s3a://warehouse/bronze/raw_trips/`)

### 7.1 Bronze with Documentation (03-bronze-raw-trips.sql)

The verbose version with inline comments explaining each decision:""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/flink/sql/03-bronze-raw-trips.sql",
    os.path.join(P01, "flink", "sql", "03-bronze-raw-trips.sql")
)

md("""### 7.2 Bronze Standalone (05-bronze.sql)

The production version used by `make process-bronze`. Identical logic, minimal comments.
Run with: `sql-client.sh embedded -i 00-init.sql -f 05-bronze.sql`""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/flink/sql/05-bronze.sql",
    os.path.join(P01, "flink", "sql", "05-bronze.sql")
)


# ── SECTION 8: Flink SQL - Silver Layer ─────────────────────────────────────
md("""## 8. Flink SQL: Silver Layer (Bronze → Cleaned Iceberg)

### What Silver Does
1. **Column renaming** → `VendorID` → `vendor_id`, `PULocationID` → `pickup_location_id`
2. **Type casting** → `BIGINT` → `INT` where appropriate, `DOUBLE` → `DECIMAL(10,2)` for money
3. **Surrogate key** → MD5 hash of composite natural key (vendor + timestamps + locations + amounts)
4. **Data quality filters:**
   - Reject null timestamps
   - Reject negative fares and distances
   - Reject dates outside January 2024
5. **Computed columns:**
   - `duration_minutes` (pickup → dropoff time difference)
   - `avg_speed_mph` (distance / time, with div-by-zero protection)
   - `cost_per_mile` (fare / distance)
   - `tip_percentage` (tip / fare × 100)
   - `pickup_date`, `pickup_hour`, `is_weekend` (time dimensions)

### 8.1 Silver with Documentation (04-silver-cleaned-trips.sql)""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/flink/sql/04-silver-cleaned-trips.sql",
    os.path.join(P01, "flink", "sql", "04-silver-cleaned-trips.sql")
)

md("""### 8.2 Silver Standalone (06-silver.sql)

Production version used by `make process-silver`.
Run with: `sql-client.sh embedded -i 00-init.sql -f 06-silver.sql`""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/flink/sql/06-silver.sql",
    os.path.join(P01, "flink", "sql", "06-silver.sql")
)


# ── SECTION 9: Flink SQL - Combined Pipeline ────────────────────────────────
md("""## 9. Flink SQL: Combined Bronze + Silver Pipeline

This single file runs both layers sequentially. Useful for understanding the
complete Flink processing flow in one place.

Run with: `sql-client.sh embedded -i 00-init.sql -f 05-run-all.sql`""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/flink/sql/05-run-all.sql",
    os.path.join(P01, "flink", "sql", "05-run-all.sql")
)


# ── SECTION 10: dbt Project Configuration ───────────────────────────────────
md("""## 10. dbt Project Configuration

dbt (data build tool) handles the **Silver → Gold** transformation layer.
It reads Iceberg Silver tables via DuckDB's `iceberg_scan()` function and
builds dimensional models (facts, dimensions, analytics marts).

### 10.1 Project Config (dbt_project.yml)

Defines project structure, materialization strategies, and seed column types.

Key patterns:
- `stg_yellow_trips` is materialized as `table` (not view) because it reads from Iceberg via DuckDB
- Intermediate models are `view` (lightweight, computed on-the-fly)
- Marts are `table` (materialized for query performance)""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/dbt_project.yml",
    os.path.join(P01, "dbt_project", "dbt_project.yml")
)

md("""### 10.2 Connection Profile (profiles.yml)

Connects dbt to DuckDB with Iceberg + S3 (MinIO) extensions.

Key settings:
- `extensions: [httpfs, parquet, iceberg]` → DuckDB can read Iceberg tables over S3
- `s3_endpoint: minio:9000` → Points to MinIO container
- `s3_url_style: path` → Required for MinIO (vs virtual-hosted for real S3)
- `memory_limit: 2GB` → DuckDB in-process memory""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/profiles.yml",
    os.path.join(P01, "dbt_project", "profiles.yml")
)

md("""### 10.3 Package Dependencies (packages.yml)

Only dependency: `dbt-utils` for utility macros (`date_spine`, `accepted_range`, etc.)""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/packages.yml",
    os.path.join(P01, "dbt_project", "packages.yml")
)

md("""### 10.4 Source Definition (sources.yml)

Defines the Iceberg Silver table as a dbt source using DuckDB's `iceberg_scan()`.

**Important:** The `identifier` uses `iceberg_scan('s3://warehouse/silver/cleaned_trips', allow_moved_paths=true)` —
this is how DuckDB reads Iceberg tables directly from S3/MinIO.""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/sources/sources.yml",
    os.path.join(P01, "dbt_project", "models", "sources", "sources.yml")
)


# ── SECTION 11: dbt Seeds ───────────────────────────────────────────────────
md("""## 11. dbt Seeds: Reference Data

Seeds are CSV files that dbt loads as tables. They provide lookup/reference data
for enriching trip records with human-readable names.

### 11.1 Payment Type Lookup""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/seeds/payment_type_lookup.csv",
    os.path.join(P01, "dbt_project", "seeds", "payment_type_lookup.csv")
)

md("### 11.2 Rate Code Lookup")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/seeds/rate_code_lookup.csv",
    os.path.join(P01, "dbt_project", "seeds", "rate_code_lookup.csv")
)

md("### 11.3 Seed Properties (column types and tests)")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/seeds/seed_properties.yml",
    os.path.join(P01, "dbt_project", "seeds", "seed_properties.yml")
)

md("""### 11.4 Taxi Zone Lookup (265 NYC zones)

Maps LocationID to borough and zone name. This is the official NYC TLC taxi zone reference.""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/seeds/taxi_zone_lookup.csv",
    os.path.join(P01, "dbt_project", "seeds", "taxi_zone_lookup.csv")
)


# ── SECTION 12: dbt Macros ──────────────────────────────────────────────────
md("""## 12. dbt Macros: Cross-Database Compatibility

These macros use dbt's `adapter.dispatch()` pattern to work across DuckDB, PostgreSQL (RisingWave),
and Spark. This means the same dbt models can be reused in Pipelines 01-11.

### 12.1 cents_to_dollars""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/macros/cents_to_dollars.sql",
    os.path.join(P01, "dbt_project", "macros", "cents_to_dollars.sql")
)

md("""### 12.2 dayname_compat, monthname_compat, mode_compat

Three adapter-dispatched macros that handle DuckDB/PostgreSQL/Spark syntax differences:
- `dayname_compat()` → `dayname()` (DuckDB) vs `to_char(..., 'Day')` (Postgres) vs `date_format(..., 'EEEE')` (Spark)
- `monthname_compat()` → Same pattern for month names
- `mode_compat()` → Statistical mode (most common value)""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/macros/dayname_compat.sql",
    os.path.join(P01, "dbt_project", "macros", "dayname_compat.sql")
)

md("### 12.3 duration_minutes")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/macros/duration_minutes.sql",
    os.path.join(P01, "dbt_project", "macros", "duration_minutes.sql")
)

md("### 12.4 test_positive_value (custom generic test)")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/macros/test_positive_value.sql",
    os.path.join(P01, "dbt_project", "macros", "test_positive_value.sql")
)


# ── SECTION 13: dbt Staging Models ──────────────────────────────────────────
md("""## 13. dbt Staging Models

Staging models are **thin wrappers** over sources. In this pipeline, Flink already
did the heavy lifting (column renaming, type casting, quality filtering), so staging
is mostly a passthrough with minor re-casting for DuckDB type compatibility.

### dbt Lineage (DAG)

```
source(raw_yellow_trips)  seed(payment_type_lookup)  seed(rate_code_lookup)  seed(taxi_zone_lookup)
         │                         │                        │                       │
         ▼                         ▼                        ▼                       ▼
  stg_yellow_trips          stg_payment_types        stg_rate_codes          stg_taxi_zones
         │                         │                        │                       │
         ▼                         │                        │                       │
  int_trip_metrics                 │                        │                       │
    │       │                      │                        │                       │
    ▼       ▼                      │                        │                       │
int_daily  int_hourly              │                        │                       │
 _summary   _patterns              │                        │                       │
    │       │                      │                        │                       │
    ▼       ▼                      ▼                        │                       ▼
mart_daily  mart_hourly      dim_payment_types              │               dim_locations
 _revenue    _demand               │                        │                  │
                                   │                        │                  │
                                   └──────────┬─────────────┘                  │
                                              ▼                                │
                                          fct_trips ◄──────────────────────────┘
                                              │
                                              ▼
                                   mart_location_performance
```

### 13.1 stg_yellow_trips.sql

The main staging model. Since Flink already cleaned the data, this is a passthrough
with safety-net null filtering and DuckDB type re-casting.""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/staging/stg_yellow_trips.sql",
    os.path.join(P01, "dbt_project", "models", "staging", "stg_yellow_trips.sql")
)

md("### 13.2 stg_payment_types.sql")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/staging/stg_payment_types.sql",
    os.path.join(P01, "dbt_project", "models", "staging", "stg_payment_types.sql")
)

md("### 13.3 stg_rate_codes.sql")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/staging/stg_rate_codes.sql",
    os.path.join(P01, "dbt_project", "models", "staging", "stg_rate_codes.sql")
)

md("### 13.4 stg_taxi_zones.sql")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/staging/stg_taxi_zones.sql",
    os.path.join(P01, "dbt_project", "models", "staging", "stg_taxi_zones.sql")
)

md("""### 13.5 staging.yml (schema + tests)

Defines **32 tests** across staging models: uniqueness, not-null, accepted values, relationships.""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/staging/staging.yml",
    os.path.join(P01, "dbt_project", "models", "staging", "staging.yml")
)


# ── SECTION 14: dbt Intermediate Models ─────────────────────────────────────
md("""## 14. dbt Intermediate Models

Intermediate models add **business logic** on top of staging. They compute metrics,
aggregate data, and apply final quality filters.

### 14.1 int_trip_metrics.sql

Enriches each trip with calculated fields:
- `trip_duration_minutes` (using adapter-dispatched macro)
- `avg_speed_mph` (with division-by-zero protection)
- `cost_per_mile`, `tip_percentage`
- `pickup_day_of_week`, `is_weekend`

Also applies final quality gates:
- Duration between 1-720 minutes
- Speed under 100 mph""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/intermediate/int_trip_metrics.sql",
    os.path.join(P01, "dbt_project", "models", "intermediate", "int_trip_metrics.sql")
)

md("### 14.2 int_daily_summary.sql\n\nOne row per day with aggregated counts, averages, and revenue totals.")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/intermediate/int_daily_summary.sql",
    os.path.join(P01, "dbt_project", "models", "intermediate", "int_daily_summary.sql")
)

md("### 14.3 int_hourly_patterns.sql\n\nOne row per date+hour combination for demand analysis.")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/intermediate/int_hourly_patterns.sql",
    os.path.join(P01, "dbt_project", "models", "intermediate", "int_hourly_patterns.sql")
)

md("### 14.4 intermediate.yml (schema + tests)")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/intermediate/intermediate.yml",
    os.path.join(P01, "dbt_project", "models", "intermediate", "intermediate.yml")
)


# ── SECTION 15: dbt Core Marts ──────────────────────────────────────────────
md("""## 15. dbt Core Marts (Gold Layer - Facts & Dimensions)

The core marts form the **Gold layer** — the final, query-ready tables for analytics.

### Star Schema Design

```
               dim_dates
                  │
                  │
dim_locations ─── fct_trips ─── dim_payment_types
                  │
                  │
           dim_locations (dropoff)
```

### 15.1 fct_trips.sql

The central **fact table**. Joins trip metrics with location dimensions.
Uses `incremental` materialization with `delete+insert` strategy for efficient rebuilds.""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/marts/core/fct_trips.sql",
    os.path.join(P01, "dbt_project", "models", "marts", "core", "fct_trips.sql")
)

md("""### 15.2 dim_dates.sql

Date dimension for January 2024. Uses `dbt_utils.date_spine()` to generate all dates,
then enriches with day-of-week, month name, weekend/holiday flags.""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/marts/core/dim_dates.sql",
    os.path.join(P01, "dbt_project", "models", "marts", "core", "dim_dates.sql")
)

md("### 15.3 dim_locations.sql\n\nTaxi zone dimension from seed data.")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/marts/core/dim_locations.sql",
    os.path.join(P01, "dbt_project", "models", "marts", "core", "dim_locations.sql")
)

md("### 15.4 dim_payment_types.sql\n\nPayment method dimension from seed data.")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/marts/core/dim_payment_types.sql",
    os.path.join(P01, "dbt_project", "models", "marts", "core", "dim_payment_types.sql")
)

md("""### 15.5 core.yml (contracts + tests)

Enforces **data contracts** on all core models — every column has a declared `data_type`.
This catches schema drift at build time.""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/marts/core/core.yml",
    os.path.join(P01, "dbt_project", "models", "marts", "core", "core.yml")
)


# ── SECTION 16: dbt Analytics Marts ─────────────────────────────────────────
md("""## 16. dbt Analytics Marts (Gold Layer - Business KPIs)

Analytics marts are purpose-built aggregations for specific business questions.

### 16.1 mart_daily_revenue.sql

Daily revenue metrics with **running totals** and **day-over-day change**.
Joins with `dim_dates` for calendar context (weekends, holidays).""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/marts/analytics/mart_daily_revenue.sql",
    os.path.join(P01, "dbt_project", "models", "marts", "analytics", "mart_daily_revenue.sql")
)

md("""### 16.2 mart_hourly_demand.sql

Hourly demand patterns aggregated across all days. Answers: "What's the average trip count at 8 AM on weekdays vs weekends?\"""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/marts/analytics/mart_hourly_demand.sql",
    os.path.join(P01, "dbt_project", "models", "marts", "analytics", "mart_hourly_demand.sql")
)

md("""### 16.3 mart_location_performance.sql

Per-zone performance summary. Includes `mode()` for most common dropoff destination and peak hour.""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/marts/analytics/mart_location_performance.sql",
    os.path.join(P01, "dbt_project", "models", "marts", "analytics", "mart_location_performance.sql")
)

md("### 16.4 analytics.yml (contracts + tests)")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/models/marts/analytics/analytics.yml",
    os.path.join(P01, "dbt_project", "models", "marts", "analytics", "analytics.yml")
)


# ── SECTION 17: dbt Tests ───────────────────────────────────────────────────
md("""## 17. dbt Tests: Data Quality Assertions

dbt tests come in two flavors:
1. **Generic tests** (in YAML files): `unique`, `not_null`, `accepted_values`, `relationships`, `accepted_range`
2. **Singular tests** (SQL files): Custom queries that return rows **only if there's a problem**

### Test Summary: 91 tests across all layers

| Layer | Tests | What They Check |
|-------|-------|-----------------|
| Staging | 32 | Uniqueness, nulls, accepted values, referential integrity |
| Intermediate | 15 | Ranges (duration 1-720 min, hour 0-23), totals > 0 |
| Core Marts | 24 | Data contracts (column types), key uniqueness |
| Analytics | 12 | Aggregation integrity, non-null results |
| Singular | 2 | fare ≤ total, duration ≥ 0 |
| Seeds | 6 | Reference data integrity |

### 17.1 assert_fare_not_exceeds_total.sql

Fare amount should never exceed total amount (which includes tips, taxes, surcharges).""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/tests/assert_fare_not_exceeds_total.sql",
    os.path.join(P01, "dbt_project", "tests", "assert_fare_not_exceeds_total.sql")
)

md("### 17.2 assert_trip_duration_positive.sql\n\nNo trip should have a negative duration (dropoff before pickup).")

writefile(
    "../pipelines/01-kafka-flink-iceberg/dbt_project/tests/assert_trip_duration_positive.sql",
    os.path.join(P01, "dbt_project", "tests", "assert_trip_duration_positive.sql")
)


# ── SECTION 18: Pipeline Makefile ────────────────────────────────────────────
md("""## 18. Pipeline Makefile: One-Command Orchestration

The Makefile provides **25+ targets** for the complete pipeline lifecycle.
Run `make help` to see all available commands.

### Key Targets

| Command | What It Does |
|---------|-------------|
| `make up` | Start all infrastructure services |
| `make down` | Stop everything, remove volumes |
| `make create-topics` | Create Kafka topic (3 partitions) |
| `make generate` | Produce 10k events (burst mode) |
| `make process` | Run Bronze + Silver Flink jobs |
| `make process-bronze` | Bronze only (Kafka → Iceberg) |
| `make process-silver` | Silver only (Bronze → Silver) |
| `make dbt-build` | dbt deps + build (full-refresh) |
| `make dbt-test` | Run 91 dbt tests |
| `make benchmark` | Full E2E: down → up → generate → process → dbt → down |
| `make status` | Show services + topics + Flink jobs |
| `make logs` | Tail all service logs |

### Critical Pattern: `MSYS_NO_PATHCONV=1`

On Windows (Git Bash/MSYS2), Docker path translation mangles Linux paths.
This env var disables it — **essential** for `docker exec` with paths like `/opt/flink/sql/`.""")

writefile(
    "../pipelines/01-kafka-flink-iceberg/Makefile",
    os.path.join(P01, "Makefile")
)


# ── SECTION 19: Airflow DAGs ────────────────────────────────────────────────
md("""## 19. Airflow DAGs: Production Scheduling

These DAGs implement the **control plane** — scheduling dbt runs and Iceberg maintenance.

> **Note:** These are reference implementations. Pipeline 01 runs Airflow via the
> optional docker-compose services. For a dedicated orchestrated pipeline, see
> Pipeline 08 (Airflow/Astronomer).

### 19.1 Pipeline DAG (every 10 minutes)

```
check_flink_health
    ├─ healthy → run_dbt → run_dbt_tests
    └─ unhealthy → alert_flink_down
```""")

# Write the Airflow DAGs as reference files
airflow_pipeline_dag = '''"""NYC Taxi Pipeline DAG - Production Orchestration.

Runs every 10 minutes:
  1. Check Flink cluster health
  2. Run dbt build (Silver → Gold)
  3. Run dbt tests (91 data quality assertions)
  4. Alert if Flink is down
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import requests


default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['alerts@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'nyc_taxi_pipeline',
    default_args=default_args,
    description='NYC Taxi Real-Time Pipeline Orchestration',
    schedule_interval='*/10 * * * *',  # Every 10 minutes
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['production', 'nyc-taxi', 'real-time'],
)


def check_flink_health(**context):
    """Check if Flink cluster is healthy and jobs are running."""
    try:
        response = requests.get('http://flink-jobmanager:8081/jobs/overview')
        response.raise_for_status()
        jobs = response.json()['jobs']
        running_jobs = [j for j in jobs if j['state'] == 'RUNNING']
        if not running_jobs:
            raise ValueError("No running Flink jobs found")
        print(f"Flink healthy: {len(running_jobs)} jobs running")
        return 'run_dbt'
    except Exception as e:
        print(f"Flink health check failed: {e}")
        return 'alert_flink_down'


# Task 1: Health check (branch based on result)
health_check = BranchPythonOperator(
    task_id='check_flink_health',
    python_callable=check_flink_health,
    provide_context=True,
    dag=dag,
)

# Task 2: Run dbt build (Silver → Gold)
run_dbt = BashOperator(
    task_id='run_dbt',
    bash_command='cd /opt/airflow/dbt && dbt build --profiles-dir . --target prod',
    dag=dag,
)

# Task 3: Run dbt tests
run_dbt_tests = BashOperator(
    task_id='run_dbt_tests',
    bash_command='cd /opt/airflow/dbt && dbt test --profiles-dir . --target prod',
    dag=dag,
)

# Task 4: Alert if Flink is unhealthy
alert_flink_down = BashOperator(
    task_id='alert_flink_down',
    bash_command='echo "ALERT: Flink cluster unhealthy" && exit 1',
    dag=dag,
)

# Dependencies
health_check >> [run_dbt, alert_flink_down]
run_dbt >> run_dbt_tests'''

code(f"%%writefile ../pipelines/01-kafka-flink-iceberg/airflow/dags/taxi_pipeline_dag.py\n{airflow_pipeline_dag}")

md("""### 19.2 Maintenance DAG (daily at 2 AM)

```
compact_silver → expire_snapshots → remove_orphan_files
```""")

maintenance_dag = '''"""Iceberg Maintenance DAG - Daily at 2 AM.

Operations:
  1. Compact Silver table (merge small files for query performance)
  2. Expire old snapshots (cleanup metadata, keep last 5)
  3. Remove orphan files (reclaim unreferenced storage)
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import timedelta


default_args = {
    'owner': 'data-engineering',
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    'iceberg_maintenance',
    default_args=default_args,
    description='Iceberg table maintenance (compaction, expiration)',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['maintenance', 'iceberg'],
)

compact_silver = BashOperator(
    task_id='compact_silver_table',
    bash_command="""
    docker exec p01-flink-jobmanager /opt/flink/bin/sql-client.sh \\
      -i /opt/flink/sql/00-init.sql \\
      -e "CALL iceberg_catalog.system.rewrite_data_files(
            table => 'nyc_taxi.silver.cleaned_trips',
            strategy => 'sort',
            sort_order => 'pickup_date,pickup_hour'
          );"
    """,
    dag=dag,
)

expire_snapshots = BashOperator(
    task_id='expire_old_snapshots',
    bash_command="""
    docker exec p01-flink-jobmanager /opt/flink/bin/sql-client.sh \\
      -i /opt/flink/sql/00-init.sql \\
      -e "CALL iceberg_catalog.system.expire_snapshots(
            table => 'nyc_taxi.silver.cleaned_trips',
            older_than => CURRENT_TIMESTAMP - INTERVAL '7' DAY,
            retain_last => 5
          );"
    """,
    dag=dag,
)

remove_orphans = BashOperator(
    task_id='remove_orphan_files',
    bash_command="""
    docker exec p01-flink-jobmanager /opt/flink/bin/sql-client.sh \\
      -i /opt/flink/sql/00-init.sql \\
      -e "CALL iceberg_catalog.system.remove_orphan_files(
            table => 'nyc_taxi.silver.cleaned_trips',
            older_than => CURRENT_TIMESTAMP - INTERVAL '7' DAY
          );"
    """,
    dag=dag,
)

compact_silver >> expire_snapshots >> remove_orphans'''

code(f"%%writefile ../pipelines/01-kafka-flink-iceberg/airflow/dags/iceberg_maintenance_dag.py\n{maintenance_dag}")


# ── SECTION 20: Running the Pipeline ────────────────────────────────────────
md("""## 20. Running the Pipeline

### Quick Start (Full Benchmark)

```bash
cd pipelines/01-kafka-flink-iceberg
make benchmark
```

This runs the complete E2E flow: `down → up → create-topics → generate → process → dbt-build → down`
Takes ~2 minutes, outputs timing to `benchmark_results/latest.json`.

### Step-by-Step Execution

```bash
# 1. Start infrastructure (Kafka, Flink, MinIO, Schema Registry)
make up
# Wait ~15-30s for all health checks to pass

# 2. Create Kafka topic
make create-topics
# Creates taxi.raw_trips with 3 partitions

# 3. Produce events
make generate
# Sends 10k events in burst mode (~0.3s)

# 4. Wait for Kafka to be fully written
sleep 10

# 5. Process Bronze layer (Kafka → Iceberg)
make process-bronze
# Runs: sql-client.sh -i 00-init.sql -f 05-bronze.sql (~24s)

# 6. Process Silver layer (Bronze → Silver Iceberg)
make process-silver
# Runs: sql-client.sh -i 00-init.sql -f 06-silver.sql (~43s)

# 7. Run dbt (Silver → Gold)
make dbt-build
# Runs: dbt deps && dbt build --full-refresh (~21s)

# 8. Verify results
make status

# 9. Clean up
make down
```

### Monitoring During Execution

| Service | URL | What to Check |
|---------|-----|---------------|
| **Flink Dashboard** | http://localhost:8081 | Running jobs, task metrics, backpressure |
| **MinIO Console** | http://localhost:9001 | Iceberg data files in `warehouse` bucket |
| **Schema Registry** | http://localhost:8085 | Registered schemas |

### Verifying Results

```bash
# Check Kafka topic offsets
docker compose exec kafka /opt/kafka/bin/kafka-run-class.sh \\
  kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic taxi.raw_trips --time -1

# Query Iceberg tables via Flink SQL
docker compose exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded \\
  -i /opt/flink/sql/00-init.sql \\
  -e "SELECT COUNT(*) FROM iceberg_catalog.bronze.raw_trips;"

docker compose exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded \\
  -i /opt/flink/sql/00-init.sql \\
  -e "SELECT COUNT(*) FROM iceberg_catalog.silver.cleaned_trips;"
```

---""")


# ── SECTION 21: Production Operations ───────────────────────────────────────
md("""## 21. Production Operations

### Performance Summary

| Phase | Duration | What Happens |
|-------|----------|-------------|
| **Infrastructure startup** | 15-30s | Services healthy, buckets created |
| **Ingestion** | 0.3s | 10k events to Kafka (31,250 evt/s) |
| **Bronze processing** | ~24s | Kafka → Iceberg (JSON parse + timestamp) |
| **Silver processing** | ~43s | Bronze → Silver (filter + enrich + write) |
| **dbt build** | ~21s | Silver → Gold (15 models, 91 tests) |
| **Total E2E** | **~107s** | First event → Gold tables ready |

### Monitoring Checklist

#### Kafka
- **Consumer lag** should approach 0 after Flink processes all data
- **Topic offsets** should match expected event count (10,000)
- **Alert if:** lag > 10,000 events for > 5 minutes

#### Flink
- **Backpressure** should be 0% (green) — check via Dashboard
- **Checkpoint duration** should be < 60s
- **Task failures** should be 0
- **Alert if:** backpressure > 10% for > 10 minutes

#### Iceberg
- **File count** should stay reasonable after compaction
- **Snapshot count** should decrease after expiration
- **Alert if:** file count > 1,000 (needs compaction)

#### dbt
- **Test failures** should be 0 (PASS=91 WARN=0 ERROR=0)
- **Source freshness** should be within SLA (< 30 minutes)
- **Alert if:** any test fails

### Scaling Considerations

| Component | Horizontal | Vertical |
|-----------|-----------|----------|
| **Kafka** | Add partitions (must match Flink parallelism) | Increase broker memory |
| **Flink** | Add task managers | Increase task slots, memory |
| **MinIO** | Add nodes (distributed mode) | Increase disk |
| **dbt** | Increase threads in profiles.yml | Increase DuckDB memory_limit |

### Backfill Pattern

```bash
# 1. Reset Kafka consumer offset
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \\
  --group flink-consumer --topic taxi.raw_trips \\
  --reset-offsets --to-earliest --execute

# 2. Re-run Flink processing
make process

# 3. Rebuild dbt from scratch
make dbt-build
```

### Companies Using This Stack

| Company | Stack |
|---------|-------|
| **Netflix** | Kafka + Flink + Iceberg |
| **Apple** | Kafka + Flink + dbt |
| **Uber** | Kafka + Flink + Hudi |
| **Airbnb** | Kafka + Spark + Iceberg + dbt |
| **LinkedIn** | Kafka + Flink + Delta Lake |
| **Stripe** | Kafka + Flink + Iceberg |

---

## Summary

### What You Built

You now have the complete source code for a **production-grade real-time data pipeline**:

- **50+ files** across shared infrastructure and pipeline-specific code
- **7 Docker services** orchestrated with health checks and dependency ordering
- **8 Flink SQL files** implementing the Bronze and Silver layers
- **15 dbt models** organized in staging → intermediate → marts (Gold)
- **91 data quality tests** covering uniqueness, nulls, ranges, relationships
- **4 cross-database macros** for portability across DuckDB/PostgreSQL/Spark
- **2 Airflow DAGs** for production scheduling and Iceberg maintenance

### File Inventory

```
shared/
├── docker/flink.Dockerfile          # Custom Flink with 7 JARs
├── docker/dbt.Dockerfile            # dbt-core + dbt-duckdb
├── data-generator/generator.py      # Parquet → Kafka producer
├── data-generator/requirements.txt  # Python dependencies
└── schemas/taxi_trip.json           # Event schema contract

pipelines/01-kafka-flink-iceberg/
├── Makefile                         # 25+ orchestration targets
├── docker-compose.yml               # 7 services
├── kafka/create-topics.sh           # Topic creation script
├── flink/conf/core-site.xml         # Hadoop S3A config
├── flink/conf/flink-conf.yaml       # Cluster configuration
├── flink/sql/00-init.sql            # Session initialization
├── flink/sql/01-create-kafka-source.sql
├── flink/sql/02-create-iceberg-catalog.sql
├── flink/sql/03-bronze-raw-trips.sql
├── flink/sql/04-silver-cleaned-trips.sql
├── flink/sql/05-bronze.sql          # Production Bronze
├── flink/sql/05-run-all.sql         # Combined Bronze+Silver
├── flink/sql/06-silver.sql          # Production Silver
├── dbt_project/
│   ├── dbt_project.yml              # Project config
│   ├── profiles.yml                 # DuckDB + Iceberg connection
│   ├── packages.yml                 # dbt-utils dependency
│   ├── macros/                      # 4 cross-database macros
│   ├── seeds/                       # 3 CSVs + properties
│   ├── models/sources/              # Iceberg Silver source
│   ├── models/staging/              # 4 staging models + tests
│   ├── models/intermediate/         # 3 intermediate models + tests
│   ├── models/marts/core/           # 4 core models + contracts
│   ├── models/marts/analytics/      # 3 analytics marts + contracts
│   └── tests/                       # 2 singular tests
└── airflow/dags/                    # 2 production DAGs
```

### Next Steps

1. **Run the pipeline:** `cd pipelines/01-kafka-flink-iceberg && make benchmark`
2. **Explore other pipelines:** Compare Kafka vs Redpanda, Flink vs Spark vs RisingWave
3. **Add orchestration:** See Pipeline 07 (Kestra), 08 (Airflow), 09 (Dagster)
4. **Add serving:** See Pipeline 10 (ClickHouse + Metabase + Superset)
5. **Add observability:** See Pipeline 11 (Elementary + Soda Core)""")


# =============================================================================
# BUILD AND WRITE THE NOTEBOOK
# =============================================================================

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.12.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

output_path = os.path.join(BASE, "notebooks", "P01_Complete_Pipeline_Notebook.ipynb")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print(f"Notebook written to: {output_path}")
print(f"Total cells: {len(cells)}")
md_cells = sum(1 for c in cells if c["cell_type"] == "markdown")
code_cells = sum(1 for c in cells if c["cell_type"] == "code")
print(f"  Markdown cells: {md_cells}")
print(f"  Code cells: {code_cells}")
writefile_cells = sum(1 for c in cells if c["cell_type"] == "code" and any("%%writefile" in s for s in c["source"]))
print(f"  %%writefile cells: {writefile_cells}")

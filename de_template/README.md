# de_template — Production-Grade Streaming Pipeline Template

A self-contained, dual-broker pipeline template: **Parquet → Broker → Flink → Iceberg → dbt**.

Works out of the box with **Redpanda** (default) or **Kafka** via a single env var change.
Includes all 16 dbt models from the NYC Taxi reference pipeline as a working example.
Designed to be adapted for any tabular dataset in ~30 minutes.

---

## Quick Start (< 30 minutes)

```bash
# 1. Put your Parquet data in data/
mkdir -p data
# cp your_file.parquet data/

# 2. Configure
cp .env.example .env
# Edit .env: DATA_PATH, TOPIC, MAX_EVENTS if needed

# 3. Start infrastructure (renders SQL + conf templates, starts Docker services)
make up

# 4. Create topics
make create-topics

# 5. Send data
make generate-limited   # 10,000 events

# 6. Process (batch)
make process            # Bronze + Silver via Flink SQL

# 7. Wait for Silver
make wait-for-silver

# 8. Build dbt models
make dbt-build

# 9. Validate end-to-end
make validate           # Expect: 4/4 PASS (+ Iceberg metadata check)
```

For a full walkthrough: [docs/00_learning_path.md](docs/00_learning_path.md)

---

## Four-Axis Configuration

Edit `.env` to change any axis. Zero SQL changes required:

| Axis | Variable | Options | Default |
|------|----------|---------|---------|
| Message broker | `BROKER` | `redpanda` \| `kafka` | `redpanda` |
| Iceberg catalog | `CATALOG` | `hadoop` \| `rest` | `hadoop` |
| Object storage | `STORAGE` | `minio` \| `aws_s3` \| `gcs` \| `azure` | `minio` |
| Processing mode | `MODE` | `batch` \| `streaming_bronze` | `batch` |

### Switch to Kafka

```bash
# Edit .env: BROKER=kafka
make down && make up && make create-topics && make generate-limited && make process && make validate
```

### Switch to AWS S3

```bash
cp .env.aws.example .env
# Edit .env: set your bucket (WAREHOUSE=s3a://YOUR-BUCKET/...) and region
# STORAGE=aws_s3 — no MinIO overlay loaded; core-site.xml rendered for IAM auth
make up
```

### Enable REST catalog (Lakekeeper)

```bash
# Edit .env: CATALOG=rest
make up EXTRA_PROFILES="--profile catalog-rest"
```

### Enable Observability (Prometheus + Grafana)

```bash
docker compose $(COMPOSE_FILES) --profile obs up -d
# Grafana: http://localhost:3000  Prometheus: http://localhost:9090
```

---

## Architecture

```
[Parquet data]
      │
      ▼ generator (burst/realtime/batch modes)
[Broker: Redpanda | Kafka]  ← hostname: broker, port 9092 (identical for all SQL)
      │
      ▼ Flink SQL batch (05_bronze_batch.sql)
[Iceberg bronze.raw_trips]         ← raw, unpartitioned, append-only
      │
      ▼ Flink SQL batch (06_silver.sql) — dedup + type casts + quality filters
[Iceberg silver.cleaned_trips]     ← partitioned by pickup_date, Iceberg v2
      │
      ▼ DuckDB iceberg_scan() via dbt
[dbt: 16 models]
  staging/         → passthrough + column aliases
  intermediate/    → trip metrics, daily aggregations, payment stats
  marts/core/      → fct_trips, dim_locations, dim_vendors, ...
  marts/analytics/ → mart_daily_revenue, mart_location_performance, ...
      │
      ▼ validate (4-stage smoke test)
  Stage 1: broker health + Flink REST + MinIO
  Stage 2: FINISHED/RUNNING job count + 0 restarts (streaming)
  Stage 3: bronze ≥ 95% produced, silver ≤ bronze, Iceberg metadata committed, DLQ ≤ DLQ_MAX
  Stage 4: dbt test (all model contracts + 2 singular tests)
```

---

## Adapting for Your Dataset

Change **4 files** to use your own data source. See [docs/03_add_new_dataset.md](docs/03_add_new_dataset.md) for step-by-step guidance including:

- How to choose your **partition column** (daily DATE always beats cardinality-based keys)
- How to choose your **dedup key** (stable under retries; use natural event ID when available)
- Full ride-share dataset example with all 4 files shown

| # | File | What to change |
|---|------|---------------|
| 1 | `.env` | `TOPIC`, `DLQ_TOPIC`, `DATA_PATH` |
| 2 | `flink/sql/05_bronze_batch.sql.tmpl` | Kafka source DDL + Bronze DDL + INSERT |
| 3 | `flink/sql/06_silver.sql.tmpl` | Silver DDL + dedup INSERT + date filter |
| 4 | `dbt/models/staging/stg_<table>.sql` | Column aliases from Silver |

The Kafka source DDL lives **inside** the Bronze script by design (not as a separate init file).
This prevents Flink SQL client session fragility that causes "Object not found" errors.

---

## File Structure

```
de_template/
├── .env.example              ← local MinIO defaults (safe to commit)
├── .env.aws.example          ← AWS S3 + IAM config pattern
├── .env.gcs.example          ← GCS config pattern
├── .env.azure.example        ← Azure ADLS config pattern
├── Makefile                  ← all targets
├── README.md
│
├── infra/                    ← Docker Compose overlays (assembled per axis)
│   ├── base.yml              ← Flink JM+TM + dbt + generator (always)
│   ├── broker.redpanda.yml   ← Redpanda v25.3.7 (hostname: broker)
│   ├── broker.kafka.yml      ← Kafka 4.0.0 KRaft (hostname: broker)
│   ├── storage.minio.yml     ← MinIO + mc-init (STORAGE=minio only)
│   ├── catalog.rest-lakekeeper.yml  ← Lakekeeper REST catalog (--profile catalog-rest)
│   ├── observability.optional.yml   ← Prometheus + Grafana (--profile obs)
│   └── prometheus.yml        ← Prometheus scrape config
│
├── docker/
│   ├── flink.Dockerfile      ← Flink 2.0.1 + 7 JARs (Iceberg, Kafka, S3A)
│   └── dbt.Dockerfile        ← Python 3.12 + dbt-duckdb + pyarrow
│
├── flink/
│   ├── conf/
│   │   ├── config.yaml               ← Flink 2.0 config (RocksDB, checkpoints, Prometheus)
│   │   ├── core-site.minio.xml.tmpl  ← Hadoop S3A for MinIO (rendered when STORAGE=minio)
│   │   └── core-site.aws.xml.tmpl    ← Hadoop S3A for AWS/cloud (rendered when STORAGE=aws_s3)
│   └── sql/                          ← SQL templates (rendered by make build-sql)
│       ├── 00_catalog.sql.tmpl           ← Iceberg Hadoop catalog init
│       ├── 00_catalog_rest.sql.tmpl      ← Iceberg REST catalog init (CATALOG=rest)
│       ├── 05_bronze_batch.sql.tmpl      ← batch Bronze: SET + Kafka DDL + Bronze DDL + INSERT
│       ├── 06_silver.sql.tmpl            ← Silver: dedup + type casts + partitioning
│       ├── 07_bronze_streaming.sql.tmpl  ← streaming Bronze (runs indefinitely)
│       ├── 01_source.sql.tmpl            ← (reference only; source DDL is in 05_bronze_batch)
│       └── 01_source_streaming.sql.tmpl  ← (reference only)
│
├── generator/                ← Parquet-to-Kafka producer
│   ├── generator.py          ← burst/realtime/batch modes
│   ├── Dockerfile
│   └── requirements.txt
│
├── schemas/
│   └── taxi_trip.json        ← JSON Schema (update for your dataset)
│
├── scripts/
│   ├── render_sql.py         ← strict template rendering (fails on ${VAR})
│   │                            also renders build/conf/core-site.xml (STORAGE-aware)
│   ├── wait_for_iceberg.py   ← polling gate: Silver rows > 0, 90s timeout
│   ├── validate.sh           ← 4-stage smoke test (incl. restart count + Iceberg metadata)
│   └── iceberg_maintenance.sh
│
├── dbt/                      ← dbt project (de_pipeline)
│   ├── dbt_project.yml
│   ├── profiles.yml          ← DuckDB + env_var() config (no hardcoded creds)
│   ├── packages.yml          ← dbt_utils ≥1.1
│   ├── models/               ← 16 models (5 staging + 3 intermediate + 5 core + 3 analytics)
│   ├── macros/               ← duration_minutes, dayname_compat, test_positive_value
│   ├── seeds/                ← 4 lookup CSVs (NYC taxi zones, payment types, etc.)
│   └── tests/                ← 2 singular tests
│
├── build/                    ← generated by make build-sql (gitignored)
│   ├── sql/                  ← rendered .sql files (Flink mounts this read-only)
│   └── conf/                 ← rendered core-site.xml (Flink mounts this read-only)
│
├── data/                     ← mount your Parquet file here (gitignored)
└── docs/
    ├── 00_learning_path.md        ← linear walkthrough
    ├── 01_stack_overview.md       ← what each component does
    ├── 02_local_quickstart.md     ← 30-min start to first validate pass
    ├── 03_add_new_dataset.md      ← 4-file changeset recipe + partition/dedup guidance
    ├── 04_batch_to_streaming.md   ← upgrade path: batch → streaming_bronze
    ├── 05_prod_deploy_notes.md    ← external broker, TLS, k8s Flink
    ├── 06_cloud_storage.md        ← MinIO vs S3/GCS/Azure endpoints
    ├── 06_secrets_and_auth.md     ← IAM-first patterns (never long-lived keys in .env)
    └── 07_observability.md        ← Flink checkpoints, broker lag, Iceberg file counts
```

---

## Key Make Targets

```bash
# Config
make print-config        # show all resolved env vars
make debug-env           # raw values with [brackets] — exposes whitespace issues
make validate-config     # fail on incompatible combinations + missing required vars

# Lifecycle
make up                  # build-sql + start infrastructure
make down                # stop + remove volumes
make health              # quick health check (BROKER-aware)

# SQL
make build-sql           # render SQL + conf templates → build/sql/ + build/conf/
make show-sql            # print all rendered SQL files + active config axes

# Topics
make create-topics       # BROKER-aware (rpk or kafka-topics.sh) + DLQ topic

# Data
make generate            # full dataset (all events)
make generate-limited    # MAX_EVENTS=10000 (smoke test)

# Processing
make process             # batch: process-bronze + process-silver
make process-bronze      # Kafka → Bronze Iceberg (batch, bounded scan)
make process-silver      # Bronze → Silver Iceberg (batch, dedup + clean)
make process-streaming   # Kafka → Bronze Iceberg (streaming, runs forever)

# Wait
make wait-for-silver     # poll Silver until rows > 0 (90s timeout)

# dbt
make dbt-build           # dbt deps + dbt build --full-refresh
make dbt-test            # dbt test only
make dbt-docs            # dbt docs generate

# Validation
make validate            # 4-stage: health + jobs + counts + dbt
make check-lag           # consumer lag + DLQ message count

# Flink job lifecycle (streaming operational control)
make flink-jobs                       # list all jobs with state + name
make flink-cancel JOB=<job-id>        # cancel a specific job
make flink-restart-streaming          # cancel all RUNNING + start fresh streaming Bronze

# Iceberg maintenance (run periodically in production)
make compact-silver      # merge small files → 128MB target
make expire-snapshots    # remove snapshots older than 7 days
make vacuum              # remove orphaned data files
make maintain            # compact-silver + expire-snapshots

# Benchmark
make benchmark           # full automated run with timing
                         # down → up → topics → generate → process → wait → dbt → down
```

---

## Template Rendering

`make build-sql` (called automatically by `make up`) renders:

- `flink/sql/*.sql.tmpl` → `build/sql/*.sql` — Flink mounts this directory read-only
- `flink/conf/core-site.xml.tmpl` → `build/conf/core-site.xml` — STORAGE-aware:
  - `STORAGE=minio`: explicit MinIO endpoint + credentials from `.env`
  - `STORAGE=aws_s3`: `DefaultAWSCredentialsProviderChain` (env vars → IAM → IRSA)

All `${VAR}` substitutions fail fast if a variable is missing from `.env`.
Use `make show-sql` to inspect rendered output before starting Flink.

---

## Version Stack

| Component | Version |
|-----------|---------|
| Flink | 2.0.1 (Java 17) |
| Iceberg | 1.10.1 |
| Kafka connector | 4.0.1-2.0 |
| Kafka (KRaft) | 4.0.0 |
| Redpanda | v25.3.7 |
| dbt-core | ≥1.8.0 |
| dbt-duckdb | ≥1.8.0 |
| DuckDB | latest |
| MinIO | RELEASE.2025-04-22 |

---

## Production Patterns Embedded

| Pattern | Location |
|---------|---------|
| `broker:9092` abstraction — same SQL for Redpanda and Kafka | `infra/broker.*.yml` |
| STORAGE-aware `core-site.xml` rendering | `scripts/render_sql.py` + `flink/conf/core-site.*.xml.tmpl` |
| Self-contained Bronze SQL (Kafka DDL inside `-f` script) | `flink/sql/05_bronze_batch.sql.tmpl` |
| RocksDB state backend + S3 checkpoints | `flink/conf/config.yaml` |
| `classloader.check-leaked-classloader: false` (Flink + Iceberg) | `flink/conf/config.yaml` |
| Prometheus metrics on Flink JM `:9249` | `flink/conf/config.yaml` |
| CPU limits: TM `2.0`, JM `1.0` | `infra/base.yml` |
| Polling gate instead of `sleep N` | `scripts/wait_for_iceberg.py` |
| DLQ topic with configurable `DLQ_MAX` threshold | Makefile + `validate.sh` |
| Flink job restart-count check in validate | `scripts/validate.sh` Stage 2 |
| Iceberg snapshot metadata committed check | `scripts/validate.sh` Stage 3 |
| `allow_moved_paths=true` in `iceberg_scan` | `dbt/models/sources/sources.yml` |
| `DUCKDB_S3_ENDPOINT` without `http://` prefix | `dbt/profiles.yml` |
| `+schema` directives (staging / intermediate / marts schemas) | `dbt/dbt_project.yml` |
| Iceberg maintenance targets (compact, expire, vacuum) | Makefile |
| `MSYS_NO_PATHCONV=1` on all docker exec calls (Windows Git Bash) | Makefile |
| Strict SQL rendering (fails fast on unsubstituted `${VAR}`) | `scripts/render_sql.py` |
| Explicit DATE column for partitioning (NOT transform expressions) | `flink/sql/06_silver.sql.tmpl` |
| `dbt deps` before `dbt build` (auto-installs packages) | Makefile |
| Flink job lifecycle targets (list / cancel / restart-streaming) | Makefile |

---

## Cloud Storage

See [docs/06_cloud_storage.md](docs/06_cloud_storage.md) for endpoint config.

For AWS S3: copy `.env.aws.example` → `.env`, set your bucket and region.
`STORAGE=aws_s3` causes `make build-sql` to render `core-site.aws.xml.tmpl`
which uses `DefaultAWSCredentialsProviderChain` — no hardcoded credentials needed
for EC2/ECS/EKS with IAM roles attached.

For GCS/Azure: start from `core-site.aws.xml.tmpl` and add the appropriate
Hadoop connector JARs to `docker/flink.Dockerfile`. See
[docs/06_secrets_and_auth.md](docs/06_secrets_and_auth.md) for IAM-first patterns.

---

## Production Deployment

See [docs/05_prod_deploy_notes.md](docs/05_prod_deploy_notes.md) for:
- External broker (SASL/TLS, MSK, Confluent Cloud)
- Managed Iceberg catalog (Glue, Nessie, Polaris)
- Kubernetes-deployed Flink (Flink Kubernetes Operator)
- Replacing MinIO with S3/GCS/Azure
- Orchestrator integration (Airflow, Dagster, Prefect)

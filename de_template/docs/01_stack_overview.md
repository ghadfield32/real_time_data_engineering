# Stack Overview

What each component does, why it's here, and what to check when it fails.

---

## Architecture Diagram

```
[Parquet file]
      │ generator.py (burst mode)
      ▼
[Broker: Redpanda | Kafka]  ← broker:9092 (internal)
      │
      │ Flink SQL Kafka source (01_source.sql)
      ▼
[Flink JobManager + TaskManager]
      │
      ├── Bronze INSERT (05_bronze.sql)   → Iceberg bronze.raw_trips
      │
      └── Silver INSERT (06_silver.sql)  → Iceberg silver.cleaned_trips
                                               (deduped + cleaned)
                                               PARTITIONED BY (pickup_date)
[MinIO | S3 | GCS | Azure]  ← object storage (s3a:// or gcs://)
      │
      │ DuckDB iceberg_scan()
      ▼
[dbt (DuckDB adapter)]
      │
      ├── staging/ (5 models, Iceberg + seed refs)
      ├── intermediate/ (3 models, metrics + aggregations)
      └── marts/ (8 models: core + analytics)
```

---

## Components

### Broker (Redpanda or Kafka)

| Property | Redpanda | Kafka |
|----------|----------|-------|
| Image | `redpandadata/redpanda:v24.3.1` | `apache/kafka:4.0.0` |
| Internal address | `broker:9092` | `broker:9092` |
| External port | `19092` | `9092` (host) |
| Mode | Single-node | KRaft (no ZooKeeper) |
| Admin UI | Redpanda Console (port 8080) | None built-in |

**Failure modes:**
- `Connection refused broker:9092` — broker not healthy yet; `make health` to check
- `UNKNOWN_TOPIC_OR_PARTITION` — run `make create-topics`
- Flink source shows 0 records — check `MAX_EVENTS` > 0 and `DATA_PATH` is readable

### Flink (JobManager + TaskManager)

- **Image**: Custom `docker/flink.Dockerfile` (FROM flink:2.0.1-java17 + 7 JARs pre-installed)
- **Config**: `flink/conf/config.yaml` (Flink 2.0 format, NOT `flink-conf.yaml`)
- **Dashboard**: http://localhost:8081
- **Metrics**: Prometheus endpoint at `:9249` on JobManager

**Failure modes:**
- Build fails with `ClassNotFoundException: org.apache.iceberg.flink...` — JARs not downloaded correctly; rebuild with `docker compose build --no-cache flink-jobmanager`
- `Object store not found` in SQL — S3A config wrong; check `flink/conf/core-site.xml` and `S3_ENDPOINT` in `.env`
- Silver table empty after bronze succeeds — check partitioning: use explicit `pickup_date DATE` column (NOT `PARTITIONED BY (days(pickup_datetime))`)
- `Unrecognized option: --configure` — wrong Flink version; ensure `flink:2.0.1-java17`

### MinIO (local object storage)

- **Image**: `minio/minio:RELEASE.2024-01-16T16-07-38Z`
- **API**: http://localhost:9000
- **Console**: http://localhost:9001 (user: minioadmin / minioadmin)
- Bucket `warehouse` is created by `mc-init` init container

**Failure modes:**
- `Access Denied` — `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` not matching MinIO root creds
- `NoSuchBucket warehouse` — `mc-init` service failed; check logs: `docker compose logs mc-init`
- DuckDB: `IO Error: S3 ... 403` — `DUCKDB_S3_ENDPOINT` must be `minio:9000` (no `http://`)

### Iceberg (table format, not a service)

- **Catalog type**: Hadoop (default, file-based on MinIO) or REST (Lakekeeper)
- **Runtime**: `iceberg-flink-runtime-2.0` JAR inside Flink container
- Metadata stored as JSON files at `s3a://warehouse/<db>/<table>/metadata/`
- Data stored as Parquet files at `s3a://warehouse/<db>/<table>/data/`

**Failure modes:**
- `Table not found` during Silver INSERT — Bronze CREATE failed silently; check Flink Dashboard for job errors; always verify row count before proceeding
- dbt: `IO Error: No files found at s3://warehouse/silver/...` — iceberg_scan has wrong path; check `WAREHOUSE` in `.env` and `sources.yml` in dbt

### dbt (DuckDB adapter)

- **Image**: `docker/dbt.Dockerfile` (python:3.12-slim + dbt-duckdb + pyarrow + pandas + duckdb)
- **Profile**: `de_pipeline` in `dbt/profiles.yml`
- **Source**: reads Silver Iceberg table via `iceberg_scan()` with `allow_moved_paths=true`
- **Seeds**: 4 lookup CSVs (vendor, payment_type, rate_code, taxi_zone)

**Failure modes:**
- `Runtime Error: No module named 'dbt.adapters.duckdb'` — adapter not installed; rebuild dbt image
- `IO Error: No files found` — stale `target/partial_parse.msgpack`; delete it before running
- `KeyError: de_pipeline` — profile name mismatch between `dbt_project.yml` and `profiles.yml`
- `cannot be used as a relation: source('raw_nyc_taxi', 'raw_yellow_trips')` — iceberg_scan failed; Silver table has 0 rows

### Lakekeeper (optional REST catalog, --profile catalog-rest)

- **Image**: `quay.io/lakekeeper/catalog:v0.11.2` (NOT Docker Hub)
- **UI**: http://localhost:8181
- **Requires**: PostgreSQL + `CATALOG=rest` in `.env` + `--profile catalog-rest` in compose command

### Prometheus + Grafana (optional observability, --profile obs)

- Prometheus scrapes Flink JM at `:9249`
- Grafana: http://localhost:3000 (admin/admin)
- See [07_observability.md](07_observability.md)

---

## Data Flow: Record Counts

For 10,000 events generated:

| Layer | Expected rows | Notes |
|-------|--------------|-------|
| Kafka topic | 10,000 | 100% of generated |
| Bronze | 9,500–10,000 | ≥95% (DLQ threshold) |
| Silver | ≤ Bronze | Dedup can only reduce |
| dbt staging | = Silver | Passthrough |
| dbt marts | < Silver | Filtered (e.g. duration > 0) |

If `silver_count > bronze_count`: impossible; indicates a bug in SQL.
If `bronze_count < 0.95 × N`: check DLQ topic for malformed records.

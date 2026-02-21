# Local Quickstart (Redpanda + MinIO, ~30 minutes)

The fastest path from zero to a working pipeline on your laptop.

---

## Prerequisites

- Docker Desktop with ≥ 8 GB RAM and ≥ 4 CPUs allocated
- `make` installed (`brew install make` / `scoop install make` / `apt install make`)
- `python3` in PATH
- NYC Taxi Parquet file for Jan 2024 (or any Parquet file)

```bash
# Download NYC taxi data (if you don't have it)
mkdir -p data
curl -L "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet" \
     -o data/yellow_tripdata_2024-01.parquet
```

---

## 1. Clone and Configure

```bash
cd de_template
cp .env.example .env
# Default .env: BROKER=redpanda, STORAGE=minio, CATALOG=hadoop, MODE=batch
# DATA_PATH and TOPIC are already set for NYC taxi data
```

Confirm config:

```bash
make print-config
```

Expected output:
```
BROKER   = redpanda
CATALOG  = hadoop
STORAGE  = minio
MODE     = batch
TOPIC    = taxi.raw_trips
WAREHOUSE= s3a://warehouse/
S3_ENDPOINT (Flink)  = http://minio:9000
DUCKDB_S3_ENDPOINT   = minio:9000
```

---

## 2. Render SQL Templates

```bash
make build-sql
```

Expected output:
```
  rendered: 00_catalog.sql.tmpl    -> build/sql/00_catalog.sql
  rendered: 01_source.sql.tmpl     -> build/sql/01_source.sql
  rendered: 05_bronze.sql.tmpl     -> build/sql/05_bronze.sql
  rendered: 06_silver.sql.tmpl     -> build/sql/06_silver.sql
  rendered: 07_streaming_bronze.sql.tmpl -> build/sql/07_streaming_bronze.sql
SQL templates rendered to build/sql/
```

---

## 3. Start Infrastructure

```bash
make up
```

First run downloads ~3 GB of images. Subsequent runs start in ~30s.

Services started:
- `template-redpanda` — Kafka-compatible broker
- `template-minio` — local S3-compatible object storage
- `template-flink-jm` — Flink JobManager (waits for healthy)
- `template-flink-tm` — Flink TaskManager (depends on JM)

```bash
make health
# Waits until all 4 services are healthy
```

Open Flink Dashboard: http://localhost:8081

---

## 4. Create Topics

```bash
make create-topics
```

Creates:
- `taxi.raw_trips` — main ingest topic (7-day retention)
- `taxi.raw_trips.dlq` — dead letter queue (7-day retention)

---

## 5. Send Data

```bash
make generate-limited
# Sends 10,000 records (MAX_EVENTS=10000)
```

Expected output:
```
Sent 10000 events in 12.3s (812 events/s)
Metrics written to /metrics/latest.json
```

---

## 6. Run Processing

```bash
make process
```

This runs two Flink SQL jobs sequentially:

**Bronze** (~40s for 10k records):
```
make process-bronze
# Flink job: read taxi.raw_trips → INSERT INTO iceberg_catalog.bronze.raw_trips
```

**Silver** (~5s):
```
make process-silver
# Flink job: deduplicate + clean → INSERT INTO iceberg_catalog.silver.cleaned_trips
```

Watch jobs complete at http://localhost:8081 (look for 2 FINISHED jobs).

---

## 7. Wait for Silver Table

```bash
make wait-for-silver
# Polls DuckDB iceberg_scan every 5s, exits when rows > 0
```

---

## 8. Build dbt Models

```bash
make dbt-build
```

Runs `dbt deps && dbt build --full-refresh` inside the dbt container.

16 models built:
- 5 staging models (stg_yellow_trips + 4 lookup stubs)
- 3 intermediate models (trip metrics, daily/hourly summaries)
- 5 core mart models (fct_trips, dim_dates, dim_locations, dim_payment_types, dim_vendors)
- 3 analytics mart models (daily_revenue, hourly_demand, location_performance)

---

## 9. Validate

```bash
make validate
```

Expected:
```
[Stage 1] Infrastructure health ............ PASS
[Stage 2] Flink job state .................. PASS (2 FINISHED)
[Stage 3] Table counts ..................... PASS
           bronze: 9855 >= 9500 (0.95 * 10000)
           silver: 9766 <= 9855
           dlq:    0 <= 0 (DLQ_MAX)
[Stage 4] dbt test ......................... PASS (all tests)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4/4 stages PASSED
```

---

## 10. Tear Down

```bash
make down
# Removes all containers and volumes
```

---

## Switch to Kafka (instead of Redpanda)

```bash
# Edit .env: BROKER=kafka
make down
make up
make create-topics
make generate-limited
make process
make validate
# Same 4/4 PASS — broker:9092 abstraction means zero SQL changes
```

---

## Troubleshooting Quick Reference

| Symptom | Fix |
|---------|-----|
| `build/sql/*.sql` has `${VAR}` literally | Missing var in `.env`; `make build-sql` will print error |
| Flink dashboard blank after `make up` | Wait 30s, retry; JM takes time to init |
| Bronze/Silver rows = 0 | Check Flink job logs at http://localhost:8081/jobs |
| dbt `IO Error: No files found` | Delete `dbt/target/partial_parse.msgpack` |
| MinIO 403 Access Denied | `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` mismatch |
| `make validate` Stage 3 FAIL | Bronze < 0.95×N; check DLQ: `make check-lag` |

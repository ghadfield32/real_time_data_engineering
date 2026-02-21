# Learning Path: de_template

A linear walkthrough for any dataset. Follow these steps in order on your first run.

---

## Step 0 — Prerequisites

- Docker Desktop ≥ 4.20 (8 GB RAM allocated, 4 CPUs)
- `make`, `git`, `python3`
- A Parquet file of your data in `data/` (e.g. `yellow_tripdata_2024-01.parquet`)

```bash
mkdir -p data
# download or copy your parquet file to data/
```

---

## Step 1 — Configure

```bash
cp .env.example .env
# Edit .env:
#   DATA_PATH=/data/your_file.parquet
#   TOPIC=your.topic.name
#   MAX_EVENTS=10000   # smoke test with subset first
```

Print all resolved axes:

```bash
make print-config
# Outputs: BROKER=redpanda, CATALOG=hadoop, STORAGE=minio, MODE=batch, ...
```

Validate axes are compatible:

```bash
make validate-config
# Fails fast if e.g. CATALOG=rest but catalog-rest profile isn't included
```

---

## Step 2 — Understand the SQL Templates

Before running anything, look at what Flink will execute:

```bash
make build-sql
# renders flink/sql/*.sql.tmpl → build/sql/*.sql
# Fails with clear error if any ${VAR} is unsubstituted
```

Read `build/sql/01_source.sql` — this is the Kafka source DDL with your topic name and broker address.
Read `build/sql/05_bronze.sql` — this is the raw INSERT into Iceberg.
Read `build/sql/06_silver.sql` — this is the dedup + clean INSERT.

---

## Step 3 — Start Infrastructure

```bash
make up
# Starts: broker (Redpanda), MinIO, Flink JM+TM
# Flink Dashboard: http://localhost:8081
# MinIO Console:  http://localhost:9001 (user: minioadmin / minioadmin)
```

Wait for all containers healthy:

```bash
make health
```

---

## Step 4 — Create Topics

```bash
make create-topics
# Creates: taxi.raw_trips (7-day retention)
#          taxi.raw_trips.dlq (7-day retention)
```

---

## Step 5 — Generate Data

```bash
make generate-limited
# Sends MAX_EVENTS=10000 records to broker:9092
# Writes {"events": 10000, ...} to metrics volume
```

Watch progress in broker UI: http://localhost:8080 (Redpanda Console, if enabled)

---

## Step 6 — Process (Batch)

```bash
make process
# Runs: process-bronze → process-silver
# process-bronze: CREATE TABLE bronze.raw_trips + INSERT from Kafka
# process-silver: CREATE TABLE silver.cleaned_trips + deduplicated INSERT
```

Follow Flink job progress: http://localhost:8081

---

## Step 7 — Wait for Silver Table

```bash
make wait-for-silver
# Polls iceberg_scan('s3://warehouse/silver/cleaned_trips') every 5s
# Exits 0 when rows > 0 (max 90s)
```

---

## Step 8 — Run dbt

```bash
make dbt-build
# docker compose run --rm dbt sh -c "dbt deps && dbt build --full-refresh"
# Runs all 16 models: staging → intermediate → marts
# Seeds: vendor_lookup, payment_type_lookup, rate_code_lookup, taxi_zone_lookup
```

---

## Step 9 — Validate End-to-End

```bash
make validate
# Stage 1: Infrastructure health (broker, Flink, MinIO)
# Stage 2: Flink job state (batch: ≥2 FINISHED; streaming: ≥1 RUNNING)
# Stage 3: Table counts (bronze ≥ 0.95×N, silver ≤ bronze, DLQ ≤ DLQ_MAX)
# Stage 4: dbt test (all tests pass)
# Expected: 4/4 PASS
```

---

## Step 10 — Tear Down

```bash
make down
# Stops containers, removes volumes (data is ephemeral locally)
```

---

## Step 11 — Full Benchmark Run

Once individual steps pass, run the automated benchmark:

```bash
make benchmark
# down → up → create-topics → generate-limited → process →
# wait-for-silver → dbt-build → validate → down
# Prints total wall-clock time
```

---

## Next Steps

- Add your own dataset: see [03_add_new_dataset.md](03_add_new_dataset.md)
- Switch to streaming mode: see [04_batch_to_streaming.md](04_batch_to_streaming.md)
- Deploy to production: see [05_prod_deploy_notes.md](05_prod_deploy_notes.md)
- Use AWS S3 instead of MinIO: see [06_cloud_storage.md](06_cloud_storage.md)

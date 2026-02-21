# Observability

What to monitor, which metrics matter, and how to set up alerts.

---

## Quick Start (Local)

Enable Prometheus + Grafana:

```bash
make up EXTRA_PROFILES="--profile obs"
# OR edit Makefile EXTRA_PROFILES line

# Access:
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000 (admin/admin)
```

Prometheus scrapes Flink JM at `:9249` every 15s (configured in `infra/prometheus.yml`).

---

## What to Watch

### 1. Flink Checkpoints (Most Important)

| Metric | Healthy value | Alert threshold |
|--------|--------------|----------------|
| `flink_jobmanager_job_lastCheckpointDuration` | < 10s | > 60s |
| `flink_jobmanager_job_numberOfFailedCheckpoints` | 0 | > 0 in 5 min |
| `flink_jobmanager_job_numberOfCompletedCheckpoints` | Incrementing | Stalled > 2 min |
| `flink_jobmanager_job_restartingTime` | 0 | > 0 (job restarted) |

**Why checkpoints matter**: Each checkpoint is a consistent snapshot of Flink state. If checkpoints fail, Flink can't guarantee exactly-once semantics. If the job crashes and can't restore from checkpoint, data may be lost or duplicated.

**Check in Flink Dashboard**: Jobs → your job → Checkpoints tab.

```bash
# Quick check via REST API:
curl -s http://localhost:8081/jobs | python3 -m json.tool
curl -s http://localhost:8081/jobs/<JOB_ID>/checkpoints | python3 -m json.tool
```

### 2. Kafka / Redpanda Consumer Lag

```bash
make check-lag
# Prints consumer group lag for flink-nyc-taxi-consumer
# Any sustained lag > 0 means Flink is behind
```

| Metric | Healthy | Alert |
|--------|---------|-------|
| Consumer lag (records) | < 1000 | > 10,000 |
| DLQ messages | 0 | > 0 (any) |
| Topic partition count | ≥ 1 | 0 (topic missing) |

**Redpanda Console** (if running): http://localhost:8080

**Kafka**: Use kafka-consumer-groups.sh or Kafka UI.

### 3. Iceberg File Health

```bash
# Count data files in Silver table:
docker compose run --rm dbt python3 - <<'EOF'
import duckdb, os
con = duckdb.connect()
con.execute("INSTALL iceberg; INSTALL httpfs; LOAD iceberg; LOAD httpfs;")
con.execute(f"SET s3_endpoint='{os.environ.get('DUCKDB_S3_ENDPOINT', 'minio:9000')}';")
con.execute("SET s3_access_key_id='minioadmin'; SET s3_use_ssl=false; SET s3_url_style='path';")
result = con.execute("""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(DISTINCT pickup_date) AS partitions
    FROM iceberg_scan('s3://warehouse/silver/cleaned_trips', allow_moved_paths=true)
""").fetchone()
print(f"Silver: {result[0]} rows across {result[1]} partitions")
EOF
```

**Small file problem**: Streaming writes create many small Parquet files (one per checkpoint). Run maintenance periodically:

```bash
make compact-silver      # merge files within each partition
make expire-snapshots    # clean up old snapshot metadata
make vacuum              # remove orphaned data files
```

### 4. MinIO / Object Storage

MinIO metrics: http://localhost:9001/api/v1/service/restart (MinIO Console → Metrics)

| Check | Command |
|-------|---------|
| Bucket exists | `docker exec template-mc mc ls local/warehouse/` |
| Silver data files | `docker exec template-mc mc ls local/warehouse/silver/cleaned_trips/data/` |
| Iceberg metadata | `docker exec template-mc mc ls local/warehouse/silver/cleaned_trips/metadata/` |

For cloud S3:

```bash
aws s3 ls s3://your-bucket/warehouse/silver/cleaned_trips/metadata/ | wc -l
# High count = many snapshots; run expire-snapshots
```

### 5. dbt Test Results

```bash
make dbt-test
# All tests must pass before production data is considered valid
```

Key tests defined in this template:

| Test | What it checks |
|------|---------------|
| `not_null` on `trip_id` | No orphan rows in Silver |
| `unique` on `trip_id` in fct_trips | Dedup worked correctly |
| `assert_trip_duration_positive` | No negative trip durations |
| `assert_fare_not_exceeds_total` | Fare logic sanity check |
| `relationships` (payment_type, rate_code) | Referential integrity with seeds |

---

## Prometheus Metrics Reference

Flink exposes metrics at `http://localhost:9249` on the JobManager.

### Key metric names (Flink 2.0)

```
# Job status
flink_jobmanager_job_uptime
flink_jobmanager_job_downtime
flink_jobmanager_job_restartingTime
flink_jobmanager_job_numberOfFailedCheckpoints
flink_jobmanager_job_numberOfCompletedCheckpoints
flink_jobmanager_job_lastCheckpointDuration
flink_jobmanager_job_lastCheckpointSize

# Task metrics
flink_taskmanager_job_task_numRecordsIn
flink_taskmanager_job_task_numRecordsOut
flink_taskmanager_job_task_numBytesIn
flink_taskmanager_job_task_numBytesOut
flink_taskmanager_job_task_isBackPressured

# JVM
flink_jobmanager_Status_JVM_Memory_Heap_Used
flink_taskmanager_Status_JVM_Memory_Heap_Used
flink_taskmanager_Status_JVM_GarbageCollector_G1_Old_Generation_Count
```

### Prometheus scrape config

`infra/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'flink'
    static_configs:
      - targets: ['flink-jobmanager:9249']
    scrape_interval: 15s
```

---

## Grafana Dashboards

Import the Flink community dashboard (ID `14301`) from Grafana.com, or create panels for:

**Row 1 — Pipeline Health**
- Total records in Bronze (gauge)
- Total records in Silver (gauge)
- DLQ count (gauge, red if > 0)

**Row 2 — Flink Performance**
- Records processed / sec (time series)
- Checkpoint duration (time series)
- Backpressure ratio (time series, alert if > 0.5)

**Row 3 — Resources**
- TaskManager heap used (time series)
- JVM GC pause time (time series)

---

## Alert Rules (Prometheus Alertmanager)

```yaml
# alerting_rules.yml
groups:
  - name: de_pipeline
    rules:
      - alert: FlinkCheckpointFailed
        expr: rate(flink_jobmanager_job_numberOfFailedCheckpoints[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Flink checkpoint failure — data at risk"

      - alert: DLQMessagesDetected
        expr: kafka_topic_partition_current_offset{topic="taxi.raw_trips.dlq"} > 0
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Dead letter queue has messages — investigate malformed records"

      - alert: FlinkJobRestarted
        expr: flink_jobmanager_job_restartingTime > 0
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Flink job restarted — check logs for root cause"
```

---

## Log Locations

```bash
# Flink JobManager logs
docker compose logs flink-jobmanager

# Flink TaskManager logs (where actual SQL execution happens)
docker compose logs flink-taskmanager

# Generator logs (records sent)
docker compose logs data-generator

# dbt logs
docker compose run --rm dbt cat /dbt/logs/dbt.log

# All logs, follow
make logs
```

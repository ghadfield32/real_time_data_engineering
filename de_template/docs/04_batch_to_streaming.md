# Batch to Streaming Upgrade Path

How to graduate from bounded batch processing (`MODE=batch`) to continuous streaming (`MODE=streaming_bronze`).

---

## What Changes

| Aspect | Batch (`MODE=batch`) | Streaming Bronze (`MODE=streaming_bronze`) |
|--------|---------------------|--------------------------------------------|
| Flink runtime mode | `BATCH` | `STREAMING` |
| Kafka source startup | `earliest-offset` | `earliest-offset` (or `latest-offset`) |
| Kafka source bounded mode | `latest-offset` (stops at end) | absent (runs forever) |
| `table.dml-sync` | `true` (Makefile waits) | absent (async) |
| Bronze job state | `FINISHED` | `RUNNING` |
| Silver job | Runs after Bronze | Separate streaming job (if applicable) |
| `make process` | Blocking | `make process-streaming` (non-blocking) |
| `make validate` Stage 2 | ≥2 FINISHED | ≥1 RUNNING |

**Key difference**: In batch mode, Flink reads the topic to the current end-of-partition, processes, and exits. In streaming mode, the job stays alive and processes new records as they arrive.

---

## Step 1 — Enable Streaming Mode

```bash
# Edit .env:
MODE=streaming_bronze
```

Render new SQL templates:

```bash
make build-sql
```

`build/sql/01_source.sql` now contains `execution.runtime-mode = 'streaming'` with no `scan.bounded.mode` and no `table.dml-sync`.

---

## Step 2 — Start Infrastructure (same as batch)

```bash
make up
make create-topics
```

---

## Step 3 — Start Continuous Bronze Job

```bash
make process-streaming
# Submits: build/sql/01_source.sql + build/sql/07_streaming_bronze.sql
# Job stays RUNNING — does NOT block the terminal
```

Verify the job is RUNNING at http://localhost:8081.

---

## Step 4 — Generate Data Continuously

In a separate terminal:

```bash
make generate-limited   # 10,000 events burst
# or
make generate           # full dataset
```

You can generate multiple times — the streaming job picks up each new batch in real time.

---

## Step 5 — Silver Processing

In `streaming_bronze` mode, Silver is still run as a separate batch job (on demand):

```bash
make process-silver
# Reads whatever is currently in bronze → writes to silver
# Run as often as needed
```

For fully continuous silver (reading from Bronze Iceberg table), you would need a separate streaming job — this is an advanced pattern not included in the template by default.

---

## Step 6 — Validate (Streaming-Aware)

```bash
make validate
```

Stage 2 now checks for ≥1 RUNNING job (not FINISHED):

```
[Stage 2] Flink job state ......... PASS (1 RUNNING, 0 restarts)
```

If the job has restarted > 0 times, Stage 2 warns but does not fail (restarts are normal during transient S3 errors).

---

## Monitoring Continuous Jobs

```bash
# Check consumer lag (how far behind Flink is)
make check-lag

# Stream Flink logs
make logs
```

**Checkpoint health**: In the Flink Dashboard → Jobs → your job → Checkpoints tab.
- `Completed checkpoints` should increment every 10s (configured in `flink/conf/config.yaml`)
- `Failed checkpoints` should be 0 after warmup

**Iceberg file growth**: Each checkpoint creates a new Iceberg data file. Run maintenance periodically:

```bash
make compact-silver      # merge small files
make expire-snapshots    # remove old snapshot metadata
```

---

## Back-Filling Historical Data

If you have historical data (before the streaming job started), run a one-off batch job first:

```bash
# 1. Start streaming job for new data
make process-streaming

# 2. In a separate step, run batch for historical range
# Edit 06_silver.sql.tmpl: adjust date range to historical period
# Re-render + process-silver
make build-sql
make process-silver
```

Iceberg supports concurrent writers (batch + streaming to the same table) with snapshot isolation.

---

## Turning Off Streaming

To stop the streaming job:

```bash
# Cancel via Flink REST API
make down    # or: docker exec template-flink-jm /opt/flink/bin/flink cancel <JOB_ID>
```

To switch back to batch:

```bash
# Edit .env: MODE=batch
make build-sql
make down && make up
make process   # blocking batch run
```

---

## When to Use Streaming vs Batch

| Use streaming when | Use batch when |
|--------------------|----------------|
| Data arrives continuously (IoT, transactions) | Data is loaded once per day/hour |
| Near-real-time dashboards required (<5 min latency) | Historical analysis is the goal |
| You want Flink to handle backpressure automatically | You need deterministic, auditable runs |
| Source topic retains data for days | Simple smoke testing or development |

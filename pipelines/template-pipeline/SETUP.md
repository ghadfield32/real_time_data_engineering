# Template Pipeline: Setup Guide
## Redpanda → Flink SQL → Iceberg (MinIO) → dbt (DuckDB)

This template turns any streaming dataset into a production-grade real-time
data pipeline in **5 file changes**. Everything else is already wired up.

---

## The 6-Question Decision Checklist

Answer these before touching any file:

| # | Question | Answer | What it affects |
|---|----------|--------|-----------------|
| 1 | **What is your Kafka topic name?** | e.g. `stock.raw_ticks` | `00-init.sql` connector, `create-topics.sh`, Makefile |
| 2 | **What does one JSON message look like?** | `rpk topic consume ... --num 1` | `00-init.sql` columns, `05-bronze.sql` columns |
| 3 | **What is your primary timestamp field?** | e.g. `trade_timestamp` | `event_time` computed column, `06-silver.sql` partition |
| 4 | **What is your natural key?** | e.g. `symbol + trade_timestamp + sequence_no` | `ROW_NUMBER() PARTITION BY` in `06-silver.sql` |
| 5 | **What date range is your data?** | e.g. `2024-01-01` to `2024-02-01` | `WHERE` filters in `06-silver.sql` |
| 6 | **What business questions do you need to answer?** | e.g. daily revenue by symbol | `models/marts/analytics/` dbt models |

---

## The 5-File Changeset

Only these 5 files change between datasets. Everything else (Docker, Flink config,
dbt infrastructure, Makefile) is copy-paste identical.

| File | What to change | Time |
|------|----------------|------|
| `flink/sql/00-init.sql` | Column list (source schema) + topic name + timestamp format | 15 min |
| `flink/sql/05-bronze.sql` | Column list (parsed types) + TO_TIMESTAMP() calls | 10 min |
| `flink/sql/06-silver.sql` | Natural key + quality filters + column renames + partition col | 20 min |
| `dbt_project/models/sources/sources.yml` | Source name + table name + iceberg_scan path | 5 min |
| `dbt_project/models/staging/stg_DOMAIN_events.sql` | Column passthrough list | 10 min |

**Total time to a working pipeline: ~60 minutes** (plus dbt mart models for your specific queries).

---

## Step-by-Step Setup

### Step 1: Clone and rename

```bash
# Copy this template to your new pipeline directory
cp -r pipelines/template-pipeline pipelines/XX-YOUR-DOMAIN

cd pipelines/XX-YOUR-DOMAIN
```

Find and replace throughout all files:
- `PIPELINE_ID` / `XX` → your pipeline number (e.g. `25`)
- `DOMAIN` → your domain name (e.g. `stock_ticks`, `orders`, `iot_sensors`)
- `PIPELINE_NAME` → your dbt project name (e.g. `stock_ticks_pipeline`)

### Step 2: Inspect your source data

```bash
# Look at a sample message from Redpanda
docker compose exec redpanda rpk topic consume DOMAIN.raw_events --num 1

# Or if reading from parquet first:
python3 -c "
import pyarrow.parquet as pq
t = pq.read_table('data/YOUR_FILE.parquet')
print(t.schema)
print(t.to_pandas().head(2).to_dict())
"
```

### Step 3: Fill in `flink/sql/00-init.sql`

Map your JSON fields to Flink SQL types:

```sql
-- Type guide:
-- text / IDs / codes → STRING
-- numeric IDs, counts → BIGINT
-- decimal values, prices → DOUBLE
-- boolean → BOOLEAN

CREATE TABLE IF NOT EXISTS kafka_raw_events (
    symbol          STRING,          -- text field
    price           DOUBLE,          -- decimal measurement
    volume          BIGINT,          -- integer count
    trade_timestamp STRING,          -- raw timestamp string (parse in bronze)
    sequence_no     BIGINT,          -- numeric ID

    event_time AS TO_TIMESTAMP(trade_timestamp, 'yyyy-MM-dd''T''HH:mm:ss'),
    WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
) WITH (
    'topic' = 'stock.raw_ticks',
    ...
```

**Copy the same column list exactly to `00-init-streaming.sql`.**

### Step 4: Fill in `flink/sql/05-bronze.sql`

Bronze = raw landing. Parse timestamps, add `ingestion_ts`, keep everything else raw:

```sql
CREATE TABLE IF NOT EXISTS bronze.raw_events (
    symbol          STRING,
    price           DOUBLE,
    volume          BIGINT,
    trade_timestamp TIMESTAMP(3),    -- parsed from STRING
    sequence_no     BIGINT,
    ingestion_ts    TIMESTAMP(3)     -- always last
) WITH (...);

INSERT INTO iceberg_catalog.bronze.raw_events
SELECT
    symbol,
    price,
    volume,
    TO_TIMESTAMP(trade_timestamp, 'yyyy-MM-dd''T''HH:mm:ss') AS trade_timestamp,
    sequence_no,
    CURRENT_TIMESTAMP AS ingestion_ts
FROM kafka_raw_events;
```

**Copy the same column list to `07-streaming-bronze.sql`.**

### Step 5: Fill in `flink/sql/06-silver.sql`

Silver = clean, typed, deduplicated, partitioned. The 5 TODO areas:

```sql
-- TODO (1/5): Silver table columns (snake_case, correct types)
CREATE TABLE IF NOT EXISTS silver.cleaned_events (
    event_id        STRING,          -- always first: MD5 surrogate key
    symbol          STRING,
    price           DECIMAL(12, 4),  -- DECIMAL for financial precision
    volume          INT,             -- INT not BIGINT where it fits
    trade_datetime  TIMESTAMP(3),
    trade_date      DATE             -- partition column, always last
) PARTITIONED BY (trade_date) ...;

-- TODO (2/5): Natural key for deduplication
ROW_NUMBER() OVER (
    PARTITION BY symbol, trade_timestamp, sequence_no
    ORDER BY ingestion_ts DESC
)

-- TODO (3/5): Quality filters
WHERE trade_timestamp IS NOT NULL
  AND price > 0
  AND volume >= 0
  AND CAST(trade_timestamp AS DATE) >= DATE '2024-01-01'
  AND CAST(trade_timestamp AS DATE) <  DATE '2024-02-01'

-- TODO (4/5): Surrogate key fields (same as PARTITION BY above)
MD5(CONCAT_WS('|', symbol, CAST(trade_timestamp AS STRING), CAST(sequence_no AS STRING)))

-- TODO (5/5): Column mapping
CAST(price AS DECIMAL(12, 4)) AS price,
CAST(volume AS INT)           AS volume,
trade_timestamp               AS trade_datetime,
CAST(trade_timestamp AS DATE) AS trade_date
```

### Step 6: Fill in `dbt_project/models/sources/sources.yml`

```yaml
sources:
  - name: raw_stock_ticks
    loaded_at_field: trade_datetime
    tables:
      - name: raw_tick_events
        config:
          external_location: "iceberg_scan('s3://warehouse/silver/cleaned_events', allow_moved_paths = true)"
```

**Path pattern:** `s3://warehouse/silver/<TABLE_NAME>`
- Table name = what Flink created: `CREATE TABLE IF NOT EXISTS silver.cleaned_events`
- → `s3://warehouse/silver/cleaned_events`

### Step 7: Fill in the staging model

Rename `stg_DOMAIN_events.sql` and fill in your column list. It's a passthrough:

```sql
with source as (
    select * from {{ source('raw_stock_ticks', 'raw_tick_events') }}
),
final as (
    select
        event_id,
        symbol,
        cast(price as decimal(12,4)) as price,
        volume,
        cast(trade_datetime as timestamp) as trade_datetime,
        trade_date
    from source
    where trade_datetime is not null
)
select * from final
```

### Step 8: Update infrastructure placeholders

In `Makefile`:
- Replace `pXX-pipeline-net` → `p25-pipeline-net` (or your number)
- Replace all `DOMAIN` → your domain name

In `docker-compose.yml`:
- Replace all `pXX` container names → `p25`
- Replace `pXX-pipeline-net` → `p25-pipeline-net`
- Replace `DOMAIN.raw_events` → your topic name
- Replace `YOUR_FILE.parquet` → your parquet filename

### Step 9: Add your dbt mart models

The staging model is the source of truth. Add mart models for business queries:

```
dbt_project/models/marts/
  core/
    dim_symbols.sql          # symbol dimension (from seeds)
    fct_trades.sql           # fact table joining staging + dimensions
  analytics/
    mart_daily_volume.sql    # aggregated: volume by symbol by day
    mart_hourly_prices.sql   # aggregated: OHLC by hour
```

### Step 10: Run the pipeline

```bash
make up
make create-topics
make generate            # or: make generate-limited for 10k events
make process             # runs Bronze then Silver
make dbt-build
make health              # verify all services OK
make check-lag           # verify DLQ is empty
```

---

## Port Conflict Reference

When running multiple pipelines simultaneously, change port mappings in `docker-compose.yml`:

| Service | Default Port | Suggested offset for pipeline N |
|---------|-------------|--------------------------------|
| Redpanda Kafka API | 19092 | 19092 + (N * 100) |
| Redpanda Console | 8085 | 8085 + N |
| Flink Dashboard | 8081 | 8081 + N |
| MinIO S3 API | 9000 | 9000 + (N * 10) |
| MinIO Console | 9001 | 9001 + (N * 10) |
| Prometheus metrics | 9249 | 9249 + N |

---

## Timestamp Format Patterns

| Data format | Flink pattern | Example |
|-------------|---------------|---------|
| `2024-01-15T09:32:11` | `'yyyy-MM-dd''T''HH:mm:ss'` | ISO 8601 no TZ |
| `2024-01-15 09:32:11` | `'yyyy-MM-dd HH:mm:ss'` | SQL datetime |
| `2024-01-15T09:32:11.123` | `'yyyy-MM-dd''T''HH:mm:ss.SSS'` | ISO 8601 with ms |
| `15/01/2024 09:32:11` | `'dd/MM/yyyy HH:mm:ss'` | European |
| Unix epoch ms (STRING) | Use `TO_TIMESTAMP_LTZ(CAST(field AS BIGINT), 3)` | e.g. `"1705309931000"` |

---

## Common Problems and Fixes

### dbt sees 0 rows after Flink process
**Cause**: Iceberg metadata commits hadn't finalized when dbt started.
**Fix**: Add `sleep 15` between `make process` and `make dbt-build`. The Makefile benchmark already includes this.

### `IO Error: No files found` in DuckDB
**Cause**: Stale `target/partial_parse.msgpack` has cached paths from a previous run.
**Fix**: `rm dbt_project/target/partial_parse.msgpack`

### Flink job fails: `Object not found: bronze.raw_events`
**Cause**: `05-bronze.sql` CREATE TABLE failed silently (usually a column type mismatch with the Kafka source).
**Fix**: Check Flink Dashboard → Job → Exceptions tab. Fix the column definition in `05-bronze.sql`.

### `Encountered '('` in Flink SQL DDL
**Cause**: `PARTITIONED BY (days(event_timestamp))` is NOT valid Flink SQL.
**Fix**: Add an explicit `DATE` column and use `PARTITIONED BY (event_date)`.

### DuckDB `s3_endpoint` error
**Cause**: You put `http://minio:9000` in profiles.yml.
**Fix**: DuckDB httpfs requires just `minio:9000` (no protocol prefix).

### Flink TaskManager OOM / S3A write timeout
**Cause**: TaskManager consuming all CPU, starving MinIO.
**Fix**: Set `cpus: '2.0'` limit on flink-taskmanager in docker-compose.yml (already set in template).

---

## Three Example Adaptations

### Stock Ticks
- Topic: `stock.raw_ticks`
- Natural key: `symbol + exchange + trade_timestamp + sequence_no`
- Partition: `trade_date` (daily)
- Silver columns: `event_id, symbol, exchange, price DECIMAL(12,4), volume INT, trade_datetime TIMESTAMP(3), trade_date DATE`
- Mart: `mart_daily_ohlc` (open/high/low/close by symbol by day)

### E-Commerce Orders
- Topic: `ecommerce.raw_orders`
- Natural key: `order_id + line_item_id`
- Partition: `order_date` (daily)
- Silver columns: `event_id, order_id, customer_id, product_id, quantity INT, unit_price DECIMAL(10,2), total_amount DECIMAL(10,2), order_datetime TIMESTAMP(3), order_date DATE`
- Mart: `mart_daily_revenue` (GMV by product_id by day)

### IoT Telemetry
- Topic: `iot.raw_telemetry`
- Natural key: `device_id + sensor_id + reading_timestamp`
- Partition: `reading_date` (daily or hourly)
- Silver columns: `event_id, device_id, sensor_id, reading_value DOUBLE, unit STRING, reading_datetime TIMESTAMP(3), reading_date DATE`
- Mart: `mart_device_daily_stats` (avg/min/max reading by device by day)

# Adding a New Dataset

Replace the NYC Taxi example with your own data. The pipeline infrastructure
(broker, Flink, Iceberg, dbt) stays identical. You only modify **4 files**.

---

## The 4-File Changeset

| # | File | What to change |
|---|------|---------------|
| 1 | `.env` | `TOPIC`, `DLQ_TOPIC`, `DATA_PATH` |
| 2 | `flink/sql/05_bronze_batch.sql.tmpl` | Kafka source DDL + Bronze table DDL + INSERT |
| 3 | `flink/sql/06_silver.sql.tmpl` | Silver table DDL, dedup INSERT, date filter |
| 4 | `dbt/models/staging/stg_<your_table>.sql` | Column aliases from Silver |

Also update `dbt/models/sources/sources.yml` to point at your Silver path,
and optionally replace seeds and intermediate/mart models for your domain.

> **Why 4 files, not 5?**
> The Kafka source DDL lives inside `05_bronze_batch.sql.tmpl` (self-contained)
> rather than in a separate `01_source.sql.tmpl`. This is by design — having
> the Kafka table DDL and the Bronze INSERT in the same `-f` script avoids a
> Flink SQL client session fragility that caused "Object not found" errors when
> using two separate `-i` scripts.

---

## Choosing Your Partition Column

**Rule:** partition by a low-cardinality time column that matches your query patterns.

| Data type | Recommended partition | Why |
|-----------|----------------------|-----|
| Time-series events | `DATE` derived from event timestamp | Daily = good scan granularity |
| High-cardinality ID (user_id, device_id) | **Do not partition on these** | Too many small files, kills scan performance |
| Pre-aggregated (daily summaries) | `report_date DATE` | Natural grain matches partition |
| CDC/changelog events | `event_date DATE` from event_ts | Keeps changelog data partitioned cleanly |

**Flink DDL rule**: `PARTITIONED BY (days(ts_col))` is **not valid** Flink SQL —
the parser rejects transform expressions. Always add an explicit `DATE` column
and use `PARTITIONED BY (pickup_date)` (or whatever you call it).

```sql
-- WRONG: parser error "Encountered '('"
PARTITIONED BY (days(event_ts))

-- RIGHT: explicit DATE column, computed in SELECT
event_date  DATE,             -- add to Silver DDL
...
PARTITIONED BY (event_date)

-- And in the INSERT SELECT:
CAST(event_ts AS DATE) AS event_date
```

---

## Choosing Your Dedup Key

**Rule:** the dedup key must be **stable under retries and replays**.

- If your upstream source has a natural event ID (`event_id`, `ride_id`,
  `transaction_id`): **use it directly** as the dedup key *and* the MD5 input.
  ```sql
  ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY ingestion_ts DESC)
  ```

- If there is no event ID: choose the minimal set of fields that together
  uniquely identify one real-world event. For NYC Taxi the key is:
  `(vendor_id, pickup_ts, dropoff_ts, pu_location, do_location, fare, total)` —
  all fields that would be the same on a duplicate but different on a real
  re-booking.

- **Avoid** including mutable or noisy fields in the key (status, updated_at,
  ingestion_ts). If those change, the key changes, and your dedup won't collapse
  duplicates.

- The MD5 surrogate key (`trip_id`) uses the same fields as the dedup key so
  it is stable across replays.

---

## Step-by-Step Example: Ride-Share Data

Suppose your Parquet schema is:

```
ride_id         STRING
driver_id       INT
pickup_ts       TIMESTAMP (serialised as ISO string in Kafka JSON)
dropoff_ts      TIMESTAMP
distance_km     DOUBLE
fare_usd        DOUBLE
tip_usd         DOUBLE
status          STRING  # completed | cancelled | dispute
```

### 1. `.env`

```ini
TOPIC=rideshare.raw_rides
DLQ_TOPIC=rideshare.raw_rides.dlq
DATA_PATH=/data/rideshare_2024-01.parquet
```

### 2. `flink/sql/05_bronze_batch.sql.tmpl`

```sql
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';

-- Kafka source: field names match Parquet column names EXACTLY (case-sensitive)
-- Timestamps arrive as ISO strings from the generator
CREATE TABLE IF NOT EXISTS kafka_raw_rides (
    ride_id         STRING,
    driver_id       INT,
    pickup_ts       STRING,
    dropoff_ts      STRING,
    distance_km     DOUBLE,
    fare_usd        DOUBLE,
    tip_usd         DOUBLE,
    status          STRING,
    event_time AS TO_TIMESTAMP(pickup_ts, 'yyyy-MM-dd''T''HH:mm:ss'),
    WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
) WITH (
    'connector'                    = 'kafka',
    'topic'                        = '${TOPIC}',
    'properties.bootstrap.servers' = 'broker:9092',
    'properties.group.id'          = 'flink-consumer',
    'scan.startup.mode'            = 'earliest-offset',
    'scan.bounded.mode'            = 'latest-offset',
    'format'                       = 'json',
    'json.ignore-parse-errors'     = 'true'
);

-- Bronze: raw landing (string timestamps preserved, no parsing here)
CREATE TABLE IF NOT EXISTS iceberg_catalog.bronze.raw_rides (
    ride_id         STRING,
    driver_id       INT,
    pickup_ts       STRING,
    dropoff_ts      STRING,
    distance_km     DOUBLE,
    fare_usd        DOUBLE,
    tip_usd         DOUBLE,
    status          STRING,
    ingestion_ts    TIMESTAMP(3)
) WITH (
    'format-version'                  = '2',
    'write.format.default'            = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);

INSERT INTO iceberg_catalog.bronze.raw_rides
SELECT
    ride_id, driver_id, pickup_ts, dropoff_ts,
    distance_km, fare_usd, tip_usd, status,
    CURRENT_TIMESTAMP AS ingestion_ts
FROM kafka_raw_rides;
```

### 3. `flink/sql/06_silver.sql.tmpl`

```sql
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';

-- TODO (1/4): Silver table column list — snake_case, correct types
--             partition column (event_date DATE) must be last
CREATE TABLE IF NOT EXISTS iceberg_catalog.silver.cleaned_rides (
    ride_id          STRING,
    driver_id        INT,
    pickup_datetime  TIMESTAMP(3),
    dropoff_datetime TIMESTAMP(3),
    distance_km      DOUBLE,
    fare_usd         DECIMAL(10, 2),
    tip_usd          DECIMAL(10, 2),
    status           STRING,
    ingestion_ts     TIMESTAMP(3),
    event_date       DATE
) PARTITIONED BY (event_date)
WITH (
    'format-version'                  = '2',
    'write.format.default'            = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);

INSERT INTO iceberg_catalog.silver.cleaned_rides
SELECT
    ride_id,
    driver_id,
    TO_TIMESTAMP(pickup_ts,  'yyyy-MM-dd''T''HH:mm:ss') AS pickup_datetime,
    TO_TIMESTAMP(dropoff_ts, 'yyyy-MM-dd''T''HH:mm:ss') AS dropoff_datetime,
    distance_km,
    CAST(fare_usd AS DECIMAL(10, 2)) AS fare_usd,
    CAST(tip_usd  AS DECIMAL(10, 2)) AS tip_usd,
    status,
    ingestion_ts,
    CAST(TO_TIMESTAMP(pickup_ts, 'yyyy-MM-dd''T''HH:mm:ss') AS DATE) AS event_date
FROM (
    SELECT *,
        -- TODO (2/4): dedup key — ride_id is a natural event ID here
        ROW_NUMBER() OVER (
            PARTITION BY ride_id
            ORDER BY ingestion_ts DESC
        ) AS rn
    FROM iceberg_catalog.bronze.raw_rides
    WHERE
        -- TODO (3/4): data quality filters
        pickup_ts IS NOT NULL
        AND dropoff_ts IS NOT NULL
        AND fare_usd >= 0
        AND distance_km >= 0
        -- TODO (4/4): date range — match your actual data dates
        AND TO_TIMESTAMP(pickup_ts, 'yyyy-MM-dd''T''HH:mm:ss') >= TIMESTAMP '2024-01-01 00:00:00'
        AND TO_TIMESTAMP(pickup_ts, 'yyyy-MM-dd''T''HH:mm:ss') <  TIMESTAMP '2024-02-01 00:00:00'
) t
WHERE rn = 1;
```

### 4. `dbt/models/staging/stg_rides.sql`

```sql
with source as (
    select * from {{ source('raw_rideshare', 'raw_rides') }}
),

renamed as (
    select
        ride_id,
        driver_id,
        pickup_datetime,
        dropoff_datetime,
        event_date,
        distance_km,
        fare_usd,
        tip_usd,
        status
    from source
    where pickup_datetime is not null
)

select * from renamed
```

Update `dbt/models/sources/sources.yml`:

```yaml
sources:
  - name: raw_rideshare
    schema: silver
    tables:
      - name: raw_rides
        description: "Silver deduplicated rides"
        external:
          location: >
            iceberg_scan('s3://warehouse/silver/cleaned_rides',
                         allow_moved_paths=true)
        loaded_at_field: pickup_datetime
        freshness:
          warn_after: {count: 24, period: hour}
          error_after: {count: 48, period: hour}
```

---

## Checklist

- [ ] `.env` — `TOPIC`, `DLQ_TOPIC`, `DATA_PATH` updated
- [ ] `05_bronze_batch.sql.tmpl` — Kafka source DDL field list + Bronze DDL + INSERT match
- [ ] `06_silver.sql.tmpl` — dedup key chosen; date range matches actual data; explicit DATE column
- [ ] Silver table `PARTITIONED BY (event_date)` — NOT `PARTITIONED BY (days(ts_col))`
- [ ] `stg_<table>.sql` — column aliases from Silver match exactly
- [ ] `sources.yml` — `external.location` points to your Silver Iceberg path
- [ ] `make build-sql` — no unsubstituted `${VAR}` errors
- [ ] `make validate` — 4/4 PASS

---

## Common Gotchas

**Flink DDL: no transform partitioning**
```sql
-- WRONG: parser error "Encountered '('"
PARTITIONED BY (days(pickup_datetime))

-- RIGHT: explicit DATE column in DDL + PARTITIONED BY (that column)
event_date DATE,
...
PARTITIONED BY (event_date)
```

**Bronze silent failure → empty Silver → vacuous dbt PASS**
If Bronze CREATE fails (wrong field name, wrong type), Silver INSERT reads
0 rows from Bronze. dbt tests then PASS vacuously (0 rows = 0 null violations).
Always run `make validate` to check actual row counts, not just dbt test status.

**String timestamps from Kafka JSON**
The generator uses Python `datetime.isoformat()` → `'2024-01-01T00:32:47'`
(T-separator, no microseconds). Parse with:
```sql
TO_TIMESTAMP(col, 'yyyy-MM-dd''T''HH:mm:ss')
```
Not `'yyyy-MM-dd HH:mm:ss'` (space separator) — that produces all-NULL results.

**Dedup key with no natural event ID**
If your source has no stable ID, use the full natural key:
all fields that together uniquely identify one real event. Do not include
`ingestion_ts` (changes on every replay) or mutable status fields.

**Bronze is append-only**
Don't add dedup logic in Bronze — that's Silver's job. Bronze is raw,
unpartitioned, append-only. Silver applies quality filters, type casts,
deduplication, and partitioning.

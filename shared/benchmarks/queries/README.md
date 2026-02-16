# Cross-Engine Benchmark Queries

Standardized SQL queries for comparing query performance across the six
analytical engines used in this project.

## Engines Covered

| Engine | SQL Dialect | Typical Table | Connection |
|---|---|---|---|
| DuckDB / Iceberg | DuckDB SQL | `fct_trips` | CLI or Python |
| ClickHouse | ClickHouse SQL | `nyc_taxi.fct_trips` | `clickhouse-client` |
| RisingWave / Materialize | PostgreSQL | `fct_trips` | `psql` |
| Apache Pinot | Pinot SQL (PQL) | `taxi_trips` | Broker REST or CLI |
| Apache Druid | Druid SQL | `taxi_trips` | Router REST or `dsql` |
| Spark SQL | Spark/Hive SQL | `nyc_taxi.fct_trips` | `spark-sql` or PySpark |

## Query Inventory

| File | Description | Complexity |
|---|---|---|
| `q1_daily_revenue.sql` | Daily revenue aggregation | Low -- single GROUP BY |
| `q2_top_locations.sql` | Top 10 pickup zones by trips and revenue | Medium -- JOIN + LIMIT |
| `q3_hourly_demand.sql` | Hourly demand heatmap (hour x day_of_week) | Medium -- two-column GROUP BY |
| `q4_payment_breakdown.sql` | Revenue breakdown by payment type | Medium -- JOIN + window function |

## How to Use

### 1. Pick the Engine Block

Each `.sql` file contains the same logical query adapted for all six engines.
Every engine variant is wrapped in a comment block.  Uncomment the block for
the engine you want to test and copy it into your client.

```text
-- ---------------------------------------------------------------------------
-- Engine 1: DuckDB / Iceberg
-- ---------------------------------------------------------------------------
-- SELECT ...
```

### 2. Run the Benchmark

Execute each query **10 times** in sequence against a warm engine (data loaded,
caches primed).  Capture the wall-clock latency for each run.

**Recommended wrapper (bash example):**

```bash
ENGINE="duckdb"
QUERY_FILE="q1_daily_revenue.sql"
RUNS=10

for i in $(seq 1 $RUNS); do
    START=$(date +%s%N)
    # Replace with the actual client invocation for your engine:
    duckdb my_database.duckdb < "$QUERY_FILE" > /dev/null
    END=$(date +%s%N)
    ELAPSED_MS=$(( (END - START) / 1000000 ))
    echo "run=$i engine=$ENGINE query=$QUERY_FILE latency_ms=$ELAPSED_MS"
done
```

### 3. Collect Percentiles

Discard the first **2 warm-up iterations** and compute statistics over the
remaining 8 runs:

| Metric | Description |
|---|---|
| **p50** | Median latency -- typical query time |
| **p95** | 95th percentile -- occasional slow path |
| **p99** | 99th percentile -- worst-case tail latency |
| **mean** | Arithmetic mean for general comparison |

### 4. Record Results

Write results into a CSV or JSON file compatible with the benchmark runner in
`../runner.py`.  Suggested schema:

```csv
engine,query,run,latency_ms
duckdb,q1_daily_revenue,1,42
duckdb,q1_daily_revenue,2,38
clickhouse,q1_daily_revenue,1,12
...
```

## Table and Column Mapping

The queries assume the following table and column conventions per engine.

### DuckDB / Iceberg, Spark SQL, ClickHouse (dbt-materialized)

These engines share the dbt mart schema:

- **fct_trips** -- fact table with enriched trip records
  - `pickup_datetime`, `dropoff_datetime` (TIMESTAMP)
  - `pickup_date` (DATE), `pickup_hour` (INT), `pickup_day_of_week` (INT)
  - `pickup_location_id`, `dropoff_location_id` (INT)
  - `pickup_zone`, `pickup_borough`, `dropoff_zone`, `dropoff_borough` (VARCHAR)
  - `payment_type_id` (INT)
  - `fare_amount`, `tip_amount`, `total_amount`, `trip_distance_miles` (DECIMAL)
- **dim_payment_types** -- payment type dimension
  - `payment_type_id` (INT), `payment_type_name` (VARCHAR)
- **dim_locations** -- taxi zone dimension
  - `location_id` (INT), `borough` (VARCHAR), `zone_name` (VARCHAR)

### Apache Pinot and Apache Druid (raw / stream-ingested)

These engines typically ingest from Kafka with raw or lightly transformed
column names:

- **taxi_trips**
  - `tpep_pickup_datetime` / `__time` (Druid)
  - `PULocationID`, `DOLocationID`
  - `payment_type` (INT -- raw code, not name)
  - `fare_amount`, `tip_amount`, `total_amount`, `trip_distance`
  - Zone names may be denormalized at ingestion or resolved via lookup

### RisingWave / Materialize

Same schema as DuckDB (`fct_trips`) when running dbt models; otherwise raw
Kafka column names if querying source tables directly.

## Tips for Fair Comparison

1. **Same data volume** -- Load the identical dataset (e.g., January 2024 Yellow
   Taxi, ~3M rows) into every engine before benchmarking.
2. **Warm caches** -- Run each query twice before starting timed iterations so
   that page caches, buffer pools, and JIT compilation are warm.
3. **Isolated environment** -- Run benchmarks on the same Docker host with no
   competing workloads.  Pin CPU/memory limits in `docker-compose.yml` for
   reproducibility.
4. **Single-client** -- Use a single concurrent client per engine to measure
   raw query latency without contention effects.
5. **Measure end-to-end** -- Capture latency from query submission to last byte
   received, not just server-side execution time, to account for serialization
   and network overhead.
6. **Document versions** -- Record the engine version, JVM flags (if applicable),
   and any non-default tuning parameters alongside results.

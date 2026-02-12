# Week 2 Notes: Seeds, Staging, and Real Data

## What We Built

- Downloaded NYC Yellow Taxi data (Jan 2024, ~3M rows, parquet format)
- Loaded reference CSVs as dbt seeds (zones, payment types, rate codes)
- Created staging models that clean and rename raw columns
- Built a simple daily summary model

## Key Takeaways

### Seeds vs Sources vs read_parquet()
| Method | Best For | Loaded By |
|--------|----------|-----------|
| Seeds (CSV) | Small reference data (<10K rows) | `dbt seed` |
| Sources (parquet) | Large raw datasets | DuckDB reads directly |
| read_parquet() | Quick prototyping (Week 2 approach) | DuckDB function |

### The Staging Pattern
Every staging model follows the same structure:
```sql
with source as (
    select * from {{ source('...') }}  -- or read_parquet() in Week 2
),
renamed as (
    select
        cast("OriginalName" as type) as snake_case_name,
        ...
    from source
)
select * from renamed
```

**Rules:**
1. One staging model per source table
2. Only rename, cast, and light filtering
3. No joins, no aggregations, no business logic

### CTEs (Common Table Expressions)
- The `with ... as (...)` pattern makes SQL readable
- Each CTE is a named logical step
- Think of them as "paragraphs" in your SQL story

### DuckDB + Parquet
- DuckDB reads parquet natively: `read_parquet('path/to/file.parquet')`
- No loading step needed -- it reads directly from the file
- Parquet is columnar, so queries that select few columns are fast

## Common Mistakes

- Forgetting to run `dbt seed` before `dbt run` (seeds must exist first)
- Using double quotes around column names that have mixed case in DuckDB
- Parquet path is relative to the DuckDB file, not the SQL file

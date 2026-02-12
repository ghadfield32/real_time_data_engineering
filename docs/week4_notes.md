# Week 4 Notes: Sources, Marts, and Documentation

## What We Built

- Defined external sources in `sources.yml` with parquet integration
- Refactored staging to use `{{ source() }}` instead of `read_parquet()`
- Built dimensional models: fact table + dimension tables
- Built analytics marts with pre-aggregated metrics
- Generated and served the dbt documentation site

## Key Takeaways

### source() vs ref()
| Function | References | Defined In |
|----------|-----------|------------|
| `{{ ref('model_name') }}` | Another dbt model | Implicit (the .sql file) |
| `{{ source('source_name', 'table_name') }}` | External data (outside dbt) | `sources.yml` |

**Why bother with source()?**
- Lineage tracking: dbt knows where your data comes from
- Documentation: column descriptions live in one place
- Freshness checks: dbt can warn if source data is stale

### dbt-duckdb External Sources
The `meta.external_location` config tells dbt-duckdb how to read external files:
```yaml
tables:
  - name: raw_yellow_trips
    meta:
      external_location: "read_parquet('../data/file.parquet')"
```

### Dimensional Modeling

**Fact tables** (`fct_*`):
- Record business events/transactions
- Contain metrics (amounts, counts, durations)
- Reference dimension tables via foreign keys
- Usually the largest tables

**Dimension tables** (`dim_*`):
- Describe the "who/what/where/when" of facts
- Contain descriptive attributes for filtering/grouping
- Usually small, slowly changing
- Examples: locations, dates, payment types

**Analytics marts** (`mart_*`):
- Pre-aggregated for specific business questions
- Trade storage for query speed
- Answer questions like "what's the daily revenue trend?"

### The Full DAG

```
Sources --> Staging --> Intermediate --> Marts (Core) --> Marts (Analytics)
(raw)      (clean)    (enrich)        (model)          (aggregate)
```

### dbt Docs
- `dbt docs generate` creates a static site from your YAML descriptions
- `dbt docs serve` hosts it locally
- The DAG view shows all model dependencies visually
- Column-level docs show descriptions and test status

## Common Mistakes

- Circular dependencies: a model can't reference itself or create a cycle
- Materializing everything as tables (wastes space/time for intermediate work)
- Not documenting models -- future you will thank present you
- Forgetting that `external_location` paths are relative to the DuckDB file

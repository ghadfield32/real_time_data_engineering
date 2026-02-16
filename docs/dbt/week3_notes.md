# Week 3 Notes: Packages, Documentation, and Testing

## What We Built

- Installed dbt packages (dbt_utils, codegen)
- Added surrogate keys to staging models
- Created schema YAML files with descriptions and tests
- Built intermediate models with calculated metrics
- Created custom macros and singular tests
- Ran the full test suite

## Key Takeaways

### dbt Packages
- Defined in `packages.yml`, installed with `dbt deps`
- **dbt_utils**: Swiss army knife -- surrogate keys, date spines, test helpers
- **codegen**: Generates YAML schema files from your models (saves typing)
- Packages install to `dbt_packages/` (gitignored)

### Surrogate Keys
- `dbt_utils.generate_surrogate_key(['col1', 'col2', ...])` creates a hash-based key
- Useful when your data has no natural primary key
- Deterministic: same inputs always produce the same key

### Testing Pyramid

```
         /\
        /  \  Singular tests (custom SQL)
       /    \
      /------\  Custom generic tests (reusable macros)
     /        \
    /----------\  dbt_utils tests (accepted_range, etc.)
   /            \
  /--------------\  Built-in generic tests (not_null, unique, etc.)
```

### Test Severity
- `error` (default): Fails the build
- `warn`: Prints a warning but doesn't fail
- Use `warn` for known data quality issues in external data
- Use `error` for things that should never happen (nulls in PKs, etc.)

### The Intermediate Layer
- Between staging and marts
- Purpose: add calculated fields, aggregate, join related staging models
- Named `int_*` by convention
- Materialized as views (they're stepping stones, not final products)

## Common Mistakes

- Running `dbt test` before `dbt run` (models must exist to test them)
- Use `dbt build` instead -- it runs seed + run + test in the right order
- Forgetting `dbt deps` after adding/changing `packages.yml`
- Tests on real data WILL fail -- that's the point! Adjust severity or fix the data.

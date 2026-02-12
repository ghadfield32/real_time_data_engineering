# Week 1 Notes: Getting Started

## What We Built

- Set up `uv` + `pyproject.toml` for Python dependency management
- Created the dbt project scaffold (`dbt init`)
- Configured project-local `profiles.yml` for DuckDB connection
- Ran example models to verify the pipeline works

## Key Takeaways

### uv vs pip
- `uv sync` replaces `pip install -r requirements.txt`
- `uv run <command>` runs commands inside the managed virtual environment
- `pyproject.toml` is the single source of truth for dependencies (replaces requirements.txt)

### dbt's Two Config Files
1. **profiles.yml** = WHERE to connect (database type, path, credentials)
2. **dbt_project.yml** = WHAT the project is (name, paths, default settings)

### Materializations
- `view`: Creates a SQL view. Fast to create, but queries execute the full SQL each time.
- `table`: Creates a physical table. Slower to create, but fast to query.
- Rule of thumb: Use `view` for staging/intermediate, `table` for marts.

### The ref() Function
- `{{ ref('model_name') }}` is how models reference each other
- dbt uses these references to build a DAG (dependency graph)
- dbt automatically builds models in the correct order

## Common Mistakes

- Forgetting `--profiles-dir .` when profiles.yml is project-local
- Mismatched profile name between `dbt_project.yml` (`profile: 'nyc_taxi_dbt'`) and `profiles.yml` (top-level key)
- Not running `uv sync` before `uv run dbt ...`

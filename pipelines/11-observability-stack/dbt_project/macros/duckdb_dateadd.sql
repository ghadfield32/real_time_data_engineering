/*
    DuckDB-compatible dateadd and timeadd overrides for Elementary compatibility.

    Two separate macro chains lead to raw `dateadd()` SQL in DuckDB:

    1. Elementary's edr_dateadd() → calls dbt.dateadd() macro
       - dbt-core defines `default__dateadd` which generates raw `dateadd(part, n, ts)`
       - dbt-core defines `postgres__dateadd` but DuckDB is NOT postgres for dispatch
       - Fix: provide `duckdb__dateadd` that generates PostgreSQL-compatible interval math

    2. Elementary's edr_timeadd() → dispatches as `adapter.dispatch('edr_timeadd', 'elementary')`
       - Falls to `default__edr_timeadd` which generates raw `dateadd(part, n, ts)`
       - Fix: provide `duckdb__edr_timeadd` using the same pattern as postgres__edr_timeadd

    DuckDB supports PostgreSQL interval arithmetic:
      timestamp + (count * interval '1 day')
*/

{% macro duckdb__dateadd(datepart, interval, from_date_or_timestamp) -%}
    {{ from_date_or_timestamp }} + (({{ interval }}) * (interval '1 {{ datepart }}'))
{%- endmacro %}

{% macro duckdb__edr_timeadd(date_part, number, timestamp_expression) -%}
    cast({{ timestamp_expression }} as timestamp) + {{ number }} * INTERVAL '1 {{ date_part }}'
{%- endmacro %}

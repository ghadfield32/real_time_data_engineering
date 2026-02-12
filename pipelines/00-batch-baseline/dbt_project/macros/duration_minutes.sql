/*
    Macro: Calculate duration between two timestamps in minutes.
    DuckDB-only version for Pipeline 00 (batch baseline).

    Usage:
        {{ duration_minutes('pickup_datetime', 'dropoff_datetime') }}
*/

{% macro duration_minutes(start_col, end_col) %}
    datediff('minute', {{ start_col }}, {{ end_col }})
{% endmacro %}

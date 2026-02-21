/*
    Macro: Calculate duration between two timestamps in minutes.
    Adapter-dispatched for DuckDB, PostgreSQL (RisingWave), and Spark.

    Usage:
        {{ duration_minutes('pickup_datetime', 'dropoff_datetime') }}
*/

{% macro duration_minutes(start_col, end_col) %}
    {{ return(adapter.dispatch('duration_minutes', 'de_pipeline')(start_col, end_col)) }}
{% endmacro %}

{% macro duckdb__duration_minutes(start_col, end_col) %}
    datediff('minute', {{ start_col }}, {{ end_col }})
{% endmacro %}

{% macro postgres__duration_minutes(start_col, end_col) %}
    (EXTRACT(EPOCH FROM ({{ end_col }} - {{ start_col }})) / 60)::bigint
{% endmacro %}

{% macro spark__duration_minutes(start_col, end_col) %}
    CAST((UNIX_TIMESTAMP({{ end_col }}) - UNIX_TIMESTAMP({{ start_col }})) / 60 AS BIGINT)
{% endmacro %}

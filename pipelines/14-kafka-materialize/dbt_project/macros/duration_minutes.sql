/*
    Macro: Calculate duration between two timestamps in minutes.
    Adapter-dispatched for PostgreSQL (Materialize).

    Usage:
        {{ duration_minutes('pickup_datetime', 'dropoff_datetime') }}
*/

{% macro duration_minutes(start_col, end_col) %}
    {{ return(adapter.dispatch('duration_minutes', 'nyc_taxi_dbt')(start_col, end_col)) }}
{% endmacro %}

{% macro postgres__duration_minutes(start_col, end_col) %}
    (EXTRACT(EPOCH FROM ({{ end_col }} - {{ start_col }})) / 60)::bigint
{% endmacro %}

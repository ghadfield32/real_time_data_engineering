-- =============================================================================
-- Macro: duration_minutes
-- =============================================================================
-- Calculates the duration in minutes between two timestamps.
-- Uses adapter dispatch for cross-database compatibility.
-- Supports: duckdb (primary), postgres/risingwave (fallback)
--
-- Usage in dbt models:
--   {{ duration_minutes('pickup_datetime', 'dropoff_datetime') }} as trip_duration_minutes
-- =============================================================================

{% macro duration_minutes(start_col, end_col) %}
    {{ return(adapter.dispatch('duration_minutes', 'nyc_taxi_dbt')(start_col, end_col)) }}
{% endmacro %}

{% macro default__duration_minutes(start_col, end_col) %}
    datediff('minute', {{ start_col }}, {{ end_col }})
{% endmacro %}

{% macro duckdb__duration_minutes(start_col, end_col) %}
    datediff('minute', {{ start_col }}, {{ end_col }})
{% endmacro %}

{% macro postgres__duration_minutes(start_col, end_col) %}
    extract(epoch from ({{ end_col }} - {{ start_col }})) / 60.0
{% endmacro %}

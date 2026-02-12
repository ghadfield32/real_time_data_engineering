/*
    Macro: Get day-of-week name from a timestamp.
    Adapter-dispatched for DuckDB, PostgreSQL (RisingWave), and Spark.

    Usage:
        {{ dayname_compat('pickup_datetime') }}
*/

{% macro dayname_compat(col) %}
    {{ return(adapter.dispatch('dayname_compat', 'nyc_taxi_pipeline_09')(col)) }}
{% endmacro %}

{% macro duckdb__dayname_compat(col) %}
    dayname({{ col }})
{% endmacro %}

{% macro postgres__dayname_compat(col) %}
    trim(to_char({{ col }}, 'Day'))
{% endmacro %}

{% macro spark__dayname_compat(col) %}
    date_format({{ col }}, 'EEEE')
{% endmacro %}


/*
    Macro: Get month name from a timestamp.
    Adapter-dispatched for DuckDB, PostgreSQL (RisingWave), and Spark.
*/

{% macro monthname_compat(col) %}
    {{ return(adapter.dispatch('monthname_compat', 'nyc_taxi_pipeline_09')(col)) }}
{% endmacro %}

{% macro duckdb__monthname_compat(col) %}
    monthname({{ col }})
{% endmacro %}

{% macro postgres__monthname_compat(col) %}
    trim(to_char({{ col }}, 'Month'))
{% endmacro %}

{% macro spark__monthname_compat(col) %}
    date_format({{ col }}, 'MMMM')
{% endmacro %}


/*
    Macro: Statistical mode (most common value).
    Adapter-dispatched for DuckDB, PostgreSQL, and Spark.
*/

{% macro mode_compat(col) %}
    {{ return(adapter.dispatch('mode_compat', 'nyc_taxi_pipeline_09')(col)) }}
{% endmacro %}

{% macro duckdb__mode_compat(col) %}
    mode({{ col }})
{% endmacro %}

{% macro postgres__mode_compat(col) %}
    mode() WITHIN GROUP (ORDER BY {{ col }})
{% endmacro %}

{% macro spark__mode_compat(col) %}
    mode({{ col }})
{% endmacro %}

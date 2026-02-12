/*
    Macro: Get day-of-week name from a timestamp.
    Adapter-dispatched for PostgreSQL (RisingWave).

    Usage:
        {{ dayname_compat('pickup_datetime') }}
*/

{% macro dayname_compat(col) %}
    {{ return(adapter.dispatch('dayname_compat', 'nyc_taxi_dbt')(col)) }}
{% endmacro %}

{% macro postgres__dayname_compat(col) %}
    trim(to_char({{ col }}, 'Day'))
{% endmacro %}


/*
    Macro: Get month name from a timestamp.
    Adapter-dispatched for PostgreSQL (RisingWave).
*/

{% macro monthname_compat(col) %}
    {{ return(adapter.dispatch('monthname_compat', 'nyc_taxi_dbt')(col)) }}
{% endmacro %}

{% macro postgres__monthname_compat(col) %}
    trim(to_char({{ col }}, 'Month'))
{% endmacro %}


/*
    Macro: Statistical mode (most common value).
    Adapter-dispatched for PostgreSQL (RisingWave).
*/

{% macro mode_compat(col) %}
    {{ return(adapter.dispatch('mode_compat', 'nyc_taxi_dbt')(col)) }}
{% endmacro %}

{% macro postgres__mode_compat(col) %}
    mode() WITHIN GROUP (ORDER BY {{ col }})
{% endmacro %}

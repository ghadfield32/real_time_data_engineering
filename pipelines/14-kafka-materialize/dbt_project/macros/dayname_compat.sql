/*
    Macro: Get day-of-week name from a timestamp.
    Adapter-dispatched for PostgreSQL (Materialize).

    IMPORTANT: The {%- -%} whitespace stripping is critical.
    Without it, Materialize's parser sees a line break before the AS alias
    and throws: "Expected a list of columns in parentheses, found AS"

    Usage:
        {{ dayname_compat('pickup_datetime') }} as day_of_week_name
*/

{% macro dayname_compat(col) %}
    {{ return(adapter.dispatch('dayname_compat', 'nyc_taxi_dbt')(col)) }}
{% endmacro %}

{% macro postgres__dayname_compat(col) -%}
trim(to_char({{ col }}, 'Day'))
{%- endmacro %}


/*
    Macro: Get month name from a timestamp.
    Adapter-dispatched for PostgreSQL (Materialize).
*/

{% macro monthname_compat(col) %}
    {{ return(adapter.dispatch('monthname_compat', 'nyc_taxi_dbt')(col)) }}
{% endmacro %}

{% macro postgres__monthname_compat(col) -%}
trim(to_char({{ col }}, 'Month'))
{%- endmacro %}


/*
    Macro: Statistical mode (most common value).
    Adapter-dispatched for PostgreSQL (Materialize).
*/

{% macro mode_compat(col) %}
    {{ return(adapter.dispatch('mode_compat', 'nyc_taxi_dbt')(col)) }}
{% endmacro %}

{% macro postgres__mode_compat(col) -%}
mode() WITHIN GROUP (ORDER BY {{ col }})
{%- endmacro %}

{% macro materialize__mode_compat(col) -%}
min({{ col }})
{%- endmacro %}

/*
    Macro: Get day-of-week name from a timestamp.
    DuckDB-only version for Pipeline 00 (batch baseline).

    Usage:
        {{ dayname_compat('pickup_datetime') }}
*/

{% macro dayname_compat(col) %}
    dayname({{ col }})
{% endmacro %}


/*
    Macro: Get month name from a timestamp.
    DuckDB-only version for Pipeline 00 (batch baseline).
*/

{% macro monthname_compat(col) %}
    monthname({{ col }})
{% endmacro %}


/*
    Macro: Statistical mode (most common value).
    DuckDB-only version for Pipeline 00 (batch baseline).
*/

{% macro mode_compat(col) %}
    mode({{ col }})
{% endmacro %}

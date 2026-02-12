/*
    Macro: Convert a cents column to dollars with rounding.

    Usage:
        {{ cents_to_dollars('fare_cents') }}
        {{ cents_to_dollars('fare_cents', 4) }}
*/

{% macro cents_to_dollars(column_name, precision=2) %}
    round(cast({{ column_name }} as decimal(10, {{ precision }})) / 100, {{ precision }})
{% endmacro %}

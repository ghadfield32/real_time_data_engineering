/*
    Macro: Calculate duration between two timestamps in minutes.

    Usage in a model:
        {{ duration_minutes('pickup_datetime', 'dropoff_datetime') }}

    Compiles to:
        datediff('minute', pickup_datetime, dropoff_datetime)
*/

{% macro duration_minutes(start_col, end_col) %}
    datediff('minute', {{ start_col }}, {{ end_col }})
{% endmacro %}

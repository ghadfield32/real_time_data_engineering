-- =============================================================================
-- Cross-Database Compatibility Macros
-- =============================================================================
-- dayname_compat:    Returns weekday name ('Monday', 'Tuesday', ...)
-- monthname_compat:  Returns month name ('January', 'February', ...)
-- mode_compat:       Returns the most frequent value in a group
--
-- Adapts to DuckDB (default) and PostgreSQL/RisingWave via adapter dispatch.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- dayname_compat
-- ---------------------------------------------------------------------------
{% macro dayname_compat(col) %}
    {{ return(adapter.dispatch('dayname_compat', 'de_pipeline')(col)) }}
{% endmacro %}

{% macro default__dayname_compat(col) %}
    dayname({{ col }})
{% endmacro %}

{% macro duckdb__dayname_compat(col) %}
    dayname({{ col }})
{% endmacro %}

{% macro postgres__dayname_compat(col) %}
    to_char({{ col }}, 'Day')
{% endmacro %}


-- ---------------------------------------------------------------------------
-- monthname_compat
-- ---------------------------------------------------------------------------
{% macro monthname_compat(col) %}
    {{ return(adapter.dispatch('monthname_compat', 'de_pipeline')(col)) }}
{% endmacro %}

{% macro default__monthname_compat(col) %}
    monthname({{ col }})
{% endmacro %}

{% macro duckdb__monthname_compat(col) %}
    monthname({{ col }})
{% endmacro %}

{% macro postgres__monthname_compat(col) %}
    to_char({{ col }}, 'Month')
{% endmacro %}


-- ---------------------------------------------------------------------------
-- mode_compat
-- ---------------------------------------------------------------------------
{% macro mode_compat(col) %}
    {{ return(adapter.dispatch('mode_compat', 'de_pipeline')(col)) }}
{% endmacro %}

{% macro default__mode_compat(col) %}
    mode() within group (order by {{ col }})
{% endmacro %}

{% macro duckdb__mode_compat(col) %}
    mode() within group (order by {{ col }})
{% endmacro %}

{% macro postgres__mode_compat(col) %}
    mode() within group (order by {{ col }})
{% endmacro %}

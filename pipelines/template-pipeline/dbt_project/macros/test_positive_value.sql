-- =============================================================================
-- Generic Test: test_positive_value
-- =============================================================================
-- Tests that all values in a column are >= 0.
-- Fails if any value is negative.
--
-- Usage in schema.yml:
--   columns:
--     - name: amount
--       tests:
--         - positive_value
-- =============================================================================
{% test positive_value(model, column_name) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} < 0
{% endtest %}

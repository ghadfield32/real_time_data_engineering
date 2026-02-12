/*
    Custom generic test: Asserts that all values in a column are >= 0.

    Usage in schema.yml:
        columns:
          - name: fare_amount
            tests:
              - positive_value

    Returns rows where the column is negative (test fails if any rows returned).
*/

{% test positive_value(model, column_name) %}

select
    {{ column_name }} as invalid_value
from {{ model }}
where {{ column_name }} < 0

{% endtest %}

/*
    Week 1 - Using ref() to chain models!

    This model references my_first_model using the ref() function.
    dbt automatically builds models in the correct order based on these references.

    The ref() function is one of dbt's most important features - it creates
    a DAG (Directed Acyclic Graph) of dependencies between your models.
*/

select
    trip_id,
    taxi_type,
    fare_amount,
    pickup_datetime,
    case
        when fare_amount > 20 then 'long'
        when fare_amount > 10 then 'medium'
        else 'short'
    end as trip_category
from {{ ref('my_first_model') }}

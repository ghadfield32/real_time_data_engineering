/*
    Singular test: fare_amount should not exceed total_amount.
*/

select
    trip_id,
    fare_amount,
    total_amount
from {{ ref('stg_yellow_trips') }}
where fare_amount > total_amount + 0.01
  and total_amount > 0

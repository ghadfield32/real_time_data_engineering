/*
    Singular test: fare_amount should not exceed total_amount.

    This catches data quality issues where the base fare
    is somehow larger than the total charged amount.
    Small tolerance (0.01) for rounding differences.
*/

select
    trip_id,
    fare_amount,
    total_amount
from {{ ref('stg_yellow_trips') }}
where fare_amount > total_amount + 0.01
  and total_amount > 0

/*
    Singular test: No trip should have negative duration.
*/

select
    trip_id,
    pickup_datetime,
    dropoff_datetime,
    trip_duration_minutes
from {{ ref('int_trip_metrics') }}
where trip_duration_minutes < 0

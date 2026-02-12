/*
    Singular test: No trip should have negative duration.

    A singular test is a standalone SQL file that returns failing rows.
    If the query returns 0 rows, the test passes.
    If it returns any rows, the test fails.
*/

select
    trip_id,
    pickup_datetime,
    dropoff_datetime,
    trip_duration_minutes
from {{ ref('int_trip_metrics') }}
where trip_duration_minutes < 0

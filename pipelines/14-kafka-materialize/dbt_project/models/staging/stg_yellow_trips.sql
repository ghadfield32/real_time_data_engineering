{#
    Staging model: Yellow taxi trip records (Materialize passthrough)

    The silver_cleaned_trips MV in Materialize already handles:
    - Column renaming and type casting
    - Quality filters (nulls, negative fares, date range)
    - Computed metrics (duration, speed, cost/mile, tip %)
    - Time dimensions (pickup_date, pickup_hour, day_of_week, is_weekend)
    - Impossible trip filters (duration 1-720 min, speed < 100 mph)

    This staging model is a simple passthrough from the source.
#}

with source as (
    select * from {{ source('raw_nyc_taxi', 'raw_yellow_trips') }}
)

select
    trip_id,
    vendor_id,
    rate_code_id,
    pickup_location_id,
    dropoff_location_id,
    payment_type_id,
    pickup_datetime,
    dropoff_datetime,
    passenger_count,
    trip_distance_miles,
    store_and_fwd_flag,
    fare_amount,
    extra_amount,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    congestion_surcharge,
    airport_fee,
    trip_duration_minutes,
    avg_speed_mph,
    cost_per_mile,
    tip_percentage,
    pickup_date,
    pickup_hour,
    pickup_day_of_week,
    is_weekend
from source

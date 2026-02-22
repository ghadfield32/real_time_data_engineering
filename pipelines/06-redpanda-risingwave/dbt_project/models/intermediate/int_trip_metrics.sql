/*
    Intermediate model: Trip-level enrichment with calculated metrics.

    For Pipeline 06 (RisingWave), the silver MV already computes all metrics.
    This model is a passthrough that preserves the same interface as other
    pipelines, ensuring downstream models (fct_trips, daily/hourly summaries)
    work unchanged.
*/

with trips as (
    select * from {{ ref('stg_yellow_trips') }}
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

    -- Already computed in RisingWave silver MV
    trip_duration_minutes,
    avg_speed_mph,
    cost_per_mile,
    tip_percentage,

    -- Time dimensions (already computed in RisingWave silver MV)
    pickup_date,
    pickup_hour,
    pickup_day_of_week,
    is_weekend,

    -- Financials passthrough
    fare_amount,
    extra_amount,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    congestion_surcharge,
    airport_fee

from trips

/*
    Fact table: Fully enriched trip records with location names.
    Incremental with delete+insert strategy.
*/

{{
  config(
    materialized='incremental',
    unique_key='trip_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
  )
}}

with trip_metrics as (
    select * from {{ ref('int_trip_metrics') }}
),

pickup_locations as (
    select * from {{ ref('dim_locations') }}
),

dropoff_locations as (
    select * from {{ ref('dim_locations') }}
),

final as (
    select
        t.trip_id,
        t.vendor_id,
        t.rate_code_id,
        t.payment_type_id,
        t.pickup_location_id,
        t.dropoff_location_id,
        t.pickup_datetime,
        t.dropoff_datetime,
        t.pickup_date,
        t.pickup_hour,
        t.pickup_day_of_week,
        t.is_weekend,
        t.passenger_count,
        t.trip_distance_miles,
        t.trip_duration_minutes,
        t.avg_speed_mph,
        t.cost_per_mile,
        t.fare_amount,
        t.extra_amount,
        t.mta_tax,
        t.tip_amount,
        t.tip_percentage,
        t.tolls_amount,
        t.improvement_surcharge,
        t.total_amount,
        t.congestion_surcharge,
        t.airport_fee,

        -- enriched from dimensions
        pu.borough as pickup_borough,
        pu.zone_name as pickup_zone,
        do_loc.borough as dropoff_borough,
        do_loc.zone_name as dropoff_zone

    from trip_metrics t
    left join pickup_locations pu
        on t.pickup_location_id = pu.location_id
    left join dropoff_locations do_loc
        on t.dropoff_location_id = do_loc.location_id

    {% if is_incremental() %}
    where t.pickup_datetime > (select max(pickup_datetime) from {{ this }})
    {% endif %}
)

select * from final

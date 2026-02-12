/*
    Intermediate model: Trip-level enrichment with calculated metrics.
    Uses adapter-dispatched macros for cross-dialect compatibility.
*/

with trips as (
    select * from {{ ref('stg_yellow_trips') }}
),

enriched as (
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

        -- calculated: duration in minutes
        {{ duration_minutes('pickup_datetime', 'dropoff_datetime') }} as trip_duration_minutes,

        -- calculated: average speed (avoid division by zero)
        case
            when {{ duration_minutes('pickup_datetime', 'dropoff_datetime') }} > 0
            then round(
                trip_distance_miles / ({{ duration_minutes('pickup_datetime', 'dropoff_datetime') }} / 60.0),
                2
            )
            else null
        end as avg_speed_mph,

        -- calculated: cost per mile
        case
            when trip_distance_miles > 0
            then round(fare_amount / trip_distance_miles, 2)
            else null
        end as cost_per_mile,

        -- calculated: tip percentage
        case
            when fare_amount > 0
            then round((tip_amount / fare_amount) * 100, 2)
            else null
        end as tip_percentage,

        -- time dimensions (using adapter-dispatched macros)
        date_trunc('day', pickup_datetime)::date as pickup_date,
        extract(hour from pickup_datetime) as pickup_hour,
        {{ dayname_compat('pickup_datetime') }} as pickup_day_of_week,
        case
            when extract(dow from pickup_datetime) in (0, 6) then true
            else false
        end as is_weekend,

        -- financials passthrough
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
)

select *
from enriched
where trip_duration_minutes between 1 and 720
  and (avg_speed_mph is null or avg_speed_mph < 100)

/*
    Analytics mart: Location-level performance summary.
    Uses adapter-dispatched mode_compat() for cross-dialect support.
*/

with trips as (
    select * from {{ ref('fct_trips') }}
),

final as (
    select
        pickup_location_id,
        pickup_borough,
        pickup_zone,

        count(*) as total_pickups,
        round(avg(trip_distance_miles), 2) as avg_trip_distance,
        round(avg(trip_duration_minutes), 2) as avg_trip_duration_min,
        round(sum(total_amount), 2) as total_revenue,
        round(avg(total_amount), 2) as avg_revenue_per_trip,
        round(avg(tip_percentage), 2) as avg_tip_pct,
        round(avg(passenger_count), 2) as avg_passengers,

        -- most common dropoff destination
        {{ mode_compat('dropoff_zone') }} as most_common_dropoff_zone,

        -- busiest hour
        {{ mode_compat('pickup_hour') }} as peak_pickup_hour

    from trips
    where pickup_zone is not null
    group by pickup_location_id, pickup_borough, pickup_zone
)

select * from final
order by total_pickups desc

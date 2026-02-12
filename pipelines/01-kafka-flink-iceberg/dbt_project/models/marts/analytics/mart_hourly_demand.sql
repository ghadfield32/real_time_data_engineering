/*
    Analytics mart: Hourly demand patterns.
*/

with hourly as (
    select * from {{ ref('int_hourly_patterns') }}
),

final as (
    select
        pickup_hour,
        is_weekend,

        count(*) as days_observed,
        round(avg(total_trips), 0) as avg_trips_per_period,
        round(avg(avg_distance), 2) as avg_distance,
        round(avg(avg_duration_min), 2) as avg_duration_min,
        round(avg(total_revenue), 2) as avg_revenue_per_period,
        sum(total_trips) as total_trips_all_days

    from hourly
    group by pickup_hour, is_weekend
)

select * from final
order by is_weekend, pickup_hour

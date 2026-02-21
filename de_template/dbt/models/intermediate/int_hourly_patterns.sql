/*
    Intermediate model: Hourly trip patterns by date.
    One row per date + hour combination.
*/

with trip_metrics as (
    select * from {{ ref('int_trip_metrics') }}
),

hourly_agg as (
    select
        pickup_date,
        pickup_hour,
        pickup_day_of_week,
        is_weekend,

        count(*) as total_trips,
        round(avg(trip_distance_miles), 2) as avg_distance,
        round(avg(trip_duration_minutes), 2) as avg_duration_min,
        round(sum(total_amount), 2) as total_revenue,
        round(avg(total_amount), 2) as avg_revenue

    from trip_metrics
    group by pickup_date, pickup_hour, pickup_day_of_week, is_weekend
)

select * from hourly_agg

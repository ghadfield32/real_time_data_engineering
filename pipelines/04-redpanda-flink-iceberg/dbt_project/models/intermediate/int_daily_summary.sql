/*
    Intermediate model: Daily aggregated trip and revenue metrics.
    One row per day with counts, averages, and revenue totals.
*/

with trip_metrics as (
    select * from {{ ref('int_trip_metrics') }}
),

daily_agg as (
    select
        pickup_date,
        pickup_day_of_week,
        is_weekend,

        count(*) as total_trips,
        sum(passenger_count) as total_passengers,

        round(avg(trip_distance_miles), 2) as avg_trip_distance,
        round(avg(trip_duration_minutes), 2) as avg_trip_duration_min,
        round(avg(avg_speed_mph), 2) as avg_speed_mph,

        round(sum(fare_amount), 2) as total_fare_revenue,
        round(sum(tip_amount), 2) as total_tip_revenue,
        round(sum(total_amount), 2) as total_revenue,
        round(avg(total_amount), 2) as avg_trip_revenue,
        round(avg(tip_percentage), 2) as avg_tip_percentage,

        count(case when payment_type_id = 1 then 1 end) as credit_card_trips,
        count(case when payment_type_id = 2 then 1 end) as cash_trips

    from trip_metrics
    group by pickup_date, pickup_day_of_week, is_weekend
)

select * from daily_agg

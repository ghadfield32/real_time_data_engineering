/*
    Analytics mart: Daily revenue metrics with running totals.
*/

with daily as (
    select * from {{ ref('int_daily_summary') }}
),

dates as (
    select * from {{ ref('dim_dates') }}
),

final as (
    select
        d.date_key,
        d.day_of_week_name,
        d.is_weekend,
        d.is_holiday,
        d.week_of_year,

        daily.total_trips,
        daily.total_passengers,
        daily.total_fare_revenue,
        daily.total_tip_revenue,
        daily.total_revenue,
        daily.avg_trip_revenue,
        daily.avg_tip_percentage,
        daily.credit_card_trips,
        daily.cash_trips,
        daily.avg_trip_distance,
        daily.avg_trip_duration_min,

        -- running total
        sum(daily.total_revenue) over (order by d.date_key) as cumulative_revenue,

        -- day-over-day change
        daily.total_revenue - lag(daily.total_revenue) over (order by d.date_key) as revenue_change_vs_prior_day

    from daily
    inner join dates d
        on daily.pickup_date = d.date_key
)

select * from final

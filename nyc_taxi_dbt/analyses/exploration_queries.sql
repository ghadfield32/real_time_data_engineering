/*
    Ad-hoc exploration queries for NYC Taxi data.

    These are NOT materialized as models -- they exist for reference
    and can be compiled with `dbt compile` to see the rendered SQL.

    Use these to explore your data before building models.
*/

-- Top 10 busiest pickup zones
select
    pickup_borough,
    pickup_zone,
    count(*) as trip_count,
    round(avg(total_amount), 2) as avg_fare
from {{ ref('fct_trips') }}
group by 1, 2
order by trip_count desc
limit 10;

-- Revenue by day of week
select
    day_of_week_name,
    is_weekend,
    round(avg(total_revenue), 2) as avg_daily_revenue,
    round(avg(total_trips), 0) as avg_daily_trips
from {{ ref('mart_daily_revenue') }}
group by 1, 2
order by avg_daily_revenue desc;

-- Payment method distribution
select
    pt.payment_type_name,
    count(*) as trip_count,
    round(count(*) * 100.0 / sum(count(*)) over (), 2) as pct_of_trips,
    round(avg(t.tip_percentage), 2) as avg_tip_pct
from {{ ref('fct_trips') }} t
left join {{ ref('dim_payment_types') }} pt
    on t.payment_type_id = pt.payment_type_id
group by 1
order by trip_count desc;

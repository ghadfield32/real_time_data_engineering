/*
    Dimension table: Calendar dates for January 2024.
    Uses generate_series for PostgreSQL/RisingWave compatibility
    (dbt_utils.date_spine may not work with all PostgreSQL variants).
*/

with date_spine as (
    select
        d::date as date_day
    from generate_series(
        '2024-01-01'::date,
        '2024-01-31'::date,
        '1 day'::interval
    ) as d
),

final as (
    select
        date_day as date_key,
        extract(year from date_day)::bigint as year,
        extract(month from date_day)::bigint as month,
        extract(day from date_day)::bigint as day_of_month,
        extract(dow from date_day)::bigint as day_of_week_num,
        {{ dayname_compat('date_day') }} as day_of_week_name,
        {{ monthname_compat('date_day') }} as month_name,
        extract(week from date_day)::bigint as week_of_year,
        case
            when extract(dow from date_day) in (0, 6) then true
            else false
        end as is_weekend,
        case
            when date_day in (
                '2024-01-01'::date,
                '2024-01-15'::date
            ) then true
            else false
        end as is_holiday

    from date_spine
)

select * from final

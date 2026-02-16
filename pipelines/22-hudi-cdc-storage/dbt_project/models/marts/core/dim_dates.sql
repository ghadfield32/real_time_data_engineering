/*
    Dimension table: Calendar dates for January 2024.
    Uses adapter-dispatched macros for dayname/monthname.
*/

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2024-01-01' as date)",
        end_date="cast('2024-02-01' as date)"
    ) }}
),

final as (
    select
        cast(date_day as date) as date_key,
        extract(year from date_day) as year,
        extract(month from date_day) as month,
        extract(day from date_day) as day_of_month,
        extract(dow from date_day) as day_of_week_num,
        {{ dayname_compat('date_day') }} as day_of_week_name,
        {{ monthname_compat('date_day') }} as month_name,
        extract(week from date_day) as week_of_year,
        case
            when extract(dow from date_day) in (0, 6) then true
            else false
        end as is_weekend,
        case
            when cast(date_day as date) in (
                cast('2024-01-01' as date),
                cast('2024-01-15' as date)
            ) then true
            else false
        end as is_holiday

    from date_spine
)

select * from final


  
    
    
      
    

    create  table
      "dev"."main"."mart_daily_revenue__dbt_tmp"
  
  (
    date_key date,
    day_of_week_name varchar,
    is_weekend boolean,
    is_holiday boolean,
    week_of_year bigint,
    total_trips bigint,
    total_passengers hugeint,
    total_fare_revenue decimal(38,2),
    total_tip_revenue decimal(38,2),
    total_revenue decimal(38,2),
    avg_trip_revenue double,
    avg_tip_percentage double,
    credit_card_trips bigint,
    cash_trips bigint,
    avg_trip_distance double,
    avg_trip_duration_min double,
    cumulative_revenue decimal(38,2),
    revenue_change_vs_prior_day decimal(38,2)
    
    )
 ;
    insert into "dev"."main"."mart_daily_revenue__dbt_tmp" 
  (
    
      
      date_key ,
    
      
      day_of_week_name ,
    
      
      is_weekend ,
    
      
      is_holiday ,
    
      
      week_of_year ,
    
      
      total_trips ,
    
      
      total_passengers ,
    
      
      total_fare_revenue ,
    
      
      total_tip_revenue ,
    
      
      total_revenue ,
    
      
      avg_trip_revenue ,
    
      
      avg_tip_percentage ,
    
      
      credit_card_trips ,
    
      
      cash_trips ,
    
      
      avg_trip_distance ,
    
      
      avg_trip_duration_min ,
    
      
      cumulative_revenue ,
    
      
      revenue_change_vs_prior_day 
    
  )
 (
      
    select date_key, day_of_week_name, is_weekend, is_holiday, week_of_year, total_trips, total_passengers, total_fare_revenue, total_tip_revenue, total_revenue, avg_trip_revenue, avg_tip_percentage, credit_card_trips, cash_trips, avg_trip_distance, avg_trip_duration_min, cumulative_revenue, revenue_change_vs_prior_day
    from (
        /*
    Analytics mart: Daily revenue metrics with running totals.
*/

with daily as (
    select * from "dev"."main"."int_daily_summary"
),

dates as (
    select * from "dev"."main"."dim_dates"
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
    ) as model_subq
    );
  
  
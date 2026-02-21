
  
    
    
      
    

    create  table
      "de_pipeline"."main_marts"."mart_hourly_demand__dbt_tmp"
  
  (
    pickup_hour bigint,
    is_weekend boolean,
    days_observed bigint,
    avg_trips_per_period double,
    avg_distance double,
    avg_duration_min double,
    avg_revenue_per_period double,
    total_trips_all_days hugeint
    
    )
 ;
    insert into "de_pipeline"."main_marts"."mart_hourly_demand__dbt_tmp" 
  (
    
      
      pickup_hour ,
    
      
      is_weekend ,
    
      
      days_observed ,
    
      
      avg_trips_per_period ,
    
      
      avg_distance ,
    
      
      avg_duration_min ,
    
      
      avg_revenue_per_period ,
    
      
      total_trips_all_days 
    
  )
 (
      
    select pickup_hour, is_weekend, days_observed, avg_trips_per_period, avg_distance, avg_duration_min, avg_revenue_per_period, total_trips_all_days
    from (
        /*
    Analytics mart: Hourly demand patterns.
*/

with hourly as (
    select * from "de_pipeline"."main_intermediate"."int_hourly_patterns"
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
    ) as model_subq
    );
  
  
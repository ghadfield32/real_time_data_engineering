
  
    
    
      
    

    create  table
      "de_pipeline"."main_marts"."mart_location_performance__dbt_tmp"
  
  (
    pickup_location_id integer,
    pickup_borough varchar,
    pickup_zone varchar,
    total_pickups bigint,
    avg_trip_distance double,
    avg_trip_duration_min double,
    total_revenue decimal(38,2),
    avg_revenue_per_trip double,
    avg_tip_pct double,
    avg_passengers double,
    most_common_dropoff_zone varchar,
    peak_pickup_hour bigint
    
    )
 ;
    insert into "de_pipeline"."main_marts"."mart_location_performance__dbt_tmp" 
  (
    
      
      pickup_location_id ,
    
      
      pickup_borough ,
    
      
      pickup_zone ,
    
      
      total_pickups ,
    
      
      avg_trip_distance ,
    
      
      avg_trip_duration_min ,
    
      
      total_revenue ,
    
      
      avg_revenue_per_trip ,
    
      
      avg_tip_pct ,
    
      
      avg_passengers ,
    
      
      most_common_dropoff_zone ,
    
      
      peak_pickup_hour 
    
  )
 (
      
    select pickup_location_id, pickup_borough, pickup_zone, total_pickups, avg_trip_distance, avg_trip_duration_min, total_revenue, avg_revenue_per_trip, avg_tip_pct, avg_passengers, most_common_dropoff_zone, peak_pickup_hour
    from (
        /*
    Analytics mart: Location-level performance summary.
    Uses adapter-dispatched mode_compat() for cross-dialect support.
*/

with trips as (
    select * from "de_pipeline"."main_marts"."fct_trips"
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
        
    mode() within group (order by dropoff_zone)
 as most_common_dropoff_zone,

        -- busiest hour
        
    mode() within group (order by pickup_hour)
 as peak_pickup_hour

    from trips
    where pickup_zone is not null
    group by pickup_location_id, pickup_borough, pickup_zone
)

select * from final
order by total_pickups desc
    ) as model_subq
    );
  
  
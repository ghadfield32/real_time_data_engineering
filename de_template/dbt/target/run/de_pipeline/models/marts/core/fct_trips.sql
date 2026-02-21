
  
    
    
      
    

    create  table
      "de_pipeline"."main_marts"."fct_trips__dbt_tmp"
  
  (
    trip_id varchar,
    vendor_id integer,
    rate_code_id integer,
    payment_type_id integer,
    pickup_location_id integer,
    dropoff_location_id integer,
    pickup_datetime timestamp,
    dropoff_datetime timestamp,
    pickup_date date,
    pickup_hour bigint,
    pickup_day_of_week varchar,
    is_weekend boolean,
    passenger_count integer,
    trip_distance_miles double,
    trip_duration_minutes bigint,
    avg_speed_mph double,
    cost_per_mile double,
    fare_amount decimal(10,2),
    extra_amount decimal(10,2),
    mta_tax decimal(10,2),
    tip_amount decimal(10,2),
    tip_percentage double,
    tolls_amount decimal(10,2),
    improvement_surcharge decimal(10,2),
    total_amount decimal(10,2),
    congestion_surcharge decimal(10,2),
    airport_fee decimal(10,2),
    pickup_borough varchar,
    pickup_zone varchar,
    dropoff_borough varchar,
    dropoff_zone varchar
    
    )
 ;
    insert into "de_pipeline"."main_marts"."fct_trips__dbt_tmp" 
  (
    
      
      trip_id ,
    
      
      vendor_id ,
    
      
      rate_code_id ,
    
      
      payment_type_id ,
    
      
      pickup_location_id ,
    
      
      dropoff_location_id ,
    
      
      pickup_datetime ,
    
      
      dropoff_datetime ,
    
      
      pickup_date ,
    
      
      pickup_hour ,
    
      
      pickup_day_of_week ,
    
      
      is_weekend ,
    
      
      passenger_count ,
    
      
      trip_distance_miles ,
    
      
      trip_duration_minutes ,
    
      
      avg_speed_mph ,
    
      
      cost_per_mile ,
    
      
      fare_amount ,
    
      
      extra_amount ,
    
      
      mta_tax ,
    
      
      tip_amount ,
    
      
      tip_percentage ,
    
      
      tolls_amount ,
    
      
      improvement_surcharge ,
    
      
      total_amount ,
    
      
      congestion_surcharge ,
    
      
      airport_fee ,
    
      
      pickup_borough ,
    
      
      pickup_zone ,
    
      
      dropoff_borough ,
    
      
      dropoff_zone 
    
  )
 (
      
    select trip_id, vendor_id, rate_code_id, payment_type_id, pickup_location_id, dropoff_location_id, pickup_datetime, dropoff_datetime, pickup_date, pickup_hour, pickup_day_of_week, is_weekend, passenger_count, trip_distance_miles, trip_duration_minutes, avg_speed_mph, cost_per_mile, fare_amount, extra_amount, mta_tax, tip_amount, tip_percentage, tolls_amount, improvement_surcharge, total_amount, congestion_surcharge, airport_fee, pickup_borough, pickup_zone, dropoff_borough, dropoff_zone
    from (
        /*
    Fact table: Fully enriched trip records with location names.
    Incremental with delete+insert strategy.
*/



with trip_metrics as (
    select * from "de_pipeline"."main_intermediate"."int_trip_metrics"
),

pickup_locations as (
    select * from "de_pipeline"."main_marts"."dim_locations"
),

dropoff_locations as (
    select * from "de_pipeline"."main_marts"."dim_locations"
),

final as (
    select
        t.trip_id,
        t.vendor_id,
        t.rate_code_id,
        t.payment_type_id,
        t.pickup_location_id,
        t.dropoff_location_id,
        t.pickup_datetime,
        t.dropoff_datetime,
        t.pickup_date,
        t.pickup_hour,
        t.pickup_day_of_week,
        t.is_weekend,
        t.passenger_count,
        t.trip_distance_miles,
        t.trip_duration_minutes,
        t.avg_speed_mph,
        t.cost_per_mile,
        t.fare_amount,
        t.extra_amount,
        t.mta_tax,
        t.tip_amount,
        t.tip_percentage,
        t.tolls_amount,
        t.improvement_surcharge,
        t.total_amount,
        t.congestion_surcharge,
        t.airport_fee,

        -- enriched from dimensions
        pu.borough as pickup_borough,
        pu.zone_name as pickup_zone,
        do_loc.borough as dropoff_borough,
        do_loc.zone_name as dropoff_zone

    from trip_metrics t
    left join pickup_locations pu
        on t.pickup_location_id = pu.location_id
    left join dropoff_locations do_loc
        on t.dropoff_location_id = do_loc.location_id

    
)

select * from final
    ) as model_subq
    );
  
  
  

  
    
    
      
    

    create  table
      "de_pipeline"."main_marts"."dim_locations__dbt_tmp"
  
  (
    location_id integer,
    borough varchar,
    zone_name varchar,
    service_zone varchar
    
    )
 ;
    insert into "de_pipeline"."main_marts"."dim_locations__dbt_tmp" 
  (
    
      
      location_id ,
    
      
      borough ,
    
      
      zone_name ,
    
      
      service_zone 
    
  )
 (
      
    select location_id, borough, zone_name, service_zone
    from (
        /*
    Dimension table: TLC Taxi Zone locations.
*/

with zones as (
    select * from "de_pipeline"."main_staging"."stg_taxi_zones"
),

final as (
    select
        location_id,
        borough,
        zone_name,
        service_zone
    from zones
)

select * from final
    ) as model_subq
    );
  
  
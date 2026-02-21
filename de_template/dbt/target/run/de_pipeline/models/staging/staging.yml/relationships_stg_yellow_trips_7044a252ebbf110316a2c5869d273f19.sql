
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select dropoff_location_id as from_field
    from "de_pipeline"."main_staging"."stg_yellow_trips"
    where dropoff_location_id is not null
),

parent as (
    select location_id as to_field
    from "de_pipeline"."main_staging"."stg_taxi_zones"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test
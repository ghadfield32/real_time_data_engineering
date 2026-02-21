
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select pickup_location_id
from "de_pipeline"."main_staging"."stg_yellow_trips"
where pickup_location_id is null



  
  
      
    ) dbt_internal_test
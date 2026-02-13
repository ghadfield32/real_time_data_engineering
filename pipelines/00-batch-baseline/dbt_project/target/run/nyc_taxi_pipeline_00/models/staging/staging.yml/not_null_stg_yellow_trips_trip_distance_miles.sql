
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select trip_distance_miles
from "dev"."main"."stg_yellow_trips"
where trip_distance_miles is null



  
  
      
    ) dbt_internal_test
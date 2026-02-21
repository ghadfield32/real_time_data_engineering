
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select pickup_hour
from "de_pipeline"."main_intermediate"."int_hourly_patterns"
where pickup_hour is null



  
  
      
    ) dbt_internal_test
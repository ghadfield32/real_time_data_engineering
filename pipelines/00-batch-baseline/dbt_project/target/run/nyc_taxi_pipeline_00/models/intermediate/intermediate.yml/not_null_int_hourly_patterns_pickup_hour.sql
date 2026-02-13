
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select pickup_hour
from "dev"."main"."int_hourly_patterns"
where pickup_hour is null



  
  
      
    ) dbt_internal_test

    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_trips
from "dev"."main"."int_hourly_patterns"
where total_trips is null



  
  
      
    ) dbt_internal_test

    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_pickups
from "dev"."main"."mart_location_performance"
where total_pickups is null



  
  
      
    ) dbt_internal_test

    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_pickups
from "de_pipeline"."main_marts"."mart_location_performance"
where total_pickups is null



  
  
      
    ) dbt_internal_test
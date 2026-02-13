
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select zone_name
from "dev"."main"."dim_locations"
where zone_name is null



  
  
      
    ) dbt_internal_test
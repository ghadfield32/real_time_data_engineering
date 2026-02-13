
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select LocationID
from "dev"."main"."taxi_zone_lookup"
where LocationID is null



  
  
      
    ) dbt_internal_test
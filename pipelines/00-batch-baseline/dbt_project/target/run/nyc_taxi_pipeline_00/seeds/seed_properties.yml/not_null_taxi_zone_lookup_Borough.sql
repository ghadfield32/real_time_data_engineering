
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select Borough
from "dev"."main"."taxi_zone_lookup"
where Borough is null



  
  
      
    ) dbt_internal_test
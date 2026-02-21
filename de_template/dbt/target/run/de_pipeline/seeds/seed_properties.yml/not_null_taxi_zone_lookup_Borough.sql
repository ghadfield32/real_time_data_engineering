
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select Borough
from "de_pipeline"."main_raw"."taxi_zone_lookup"
where Borough is null



  
  
      
    ) dbt_internal_test
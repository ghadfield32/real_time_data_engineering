
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select LocationID
from "de_pipeline"."main_raw"."taxi_zone_lookup"
where LocationID is null



  
  
      
    ) dbt_internal_test
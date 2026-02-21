
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select vendor_abbr
from "de_pipeline"."main_raw"."vendor_lookup"
where vendor_abbr is null



  
  
      
    ) dbt_internal_test
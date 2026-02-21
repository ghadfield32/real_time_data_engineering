
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select payment_type_id
from "de_pipeline"."main_raw"."payment_type_lookup"
where payment_type_id is null



  
  
      
    ) dbt_internal_test
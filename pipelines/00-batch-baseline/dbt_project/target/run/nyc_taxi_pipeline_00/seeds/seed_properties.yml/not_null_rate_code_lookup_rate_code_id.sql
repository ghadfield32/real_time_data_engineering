
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select rate_code_id
from "dev"."main"."rate_code_lookup"
where rate_code_id is null



  
  
      
    ) dbt_internal_test
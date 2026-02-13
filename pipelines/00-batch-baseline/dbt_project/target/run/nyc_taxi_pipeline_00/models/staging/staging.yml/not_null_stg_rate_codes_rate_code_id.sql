
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select rate_code_id
from "dev"."main"."stg_rate_codes"
where rate_code_id is null



  
  
      
    ) dbt_internal_test
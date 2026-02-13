
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select rate_code_name
from "dev"."main"."stg_rate_codes"
where rate_code_name is null



  
  
      
    ) dbt_internal_test
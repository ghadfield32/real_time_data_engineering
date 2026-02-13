
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select payment_type_name
from "dev"."main"."stg_payment_types"
where payment_type_name is null



  
  
      
    ) dbt_internal_test
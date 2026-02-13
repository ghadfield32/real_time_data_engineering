
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select payment_type_id
from "dev"."main"."dim_payment_types"
where payment_type_id is null



  
  
      
    ) dbt_internal_test
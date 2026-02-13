
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select fare_amount
from "dev"."main"."stg_yellow_trips"
where fare_amount is null



  
  
      
    ) dbt_internal_test

    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_amount
from "de_pipeline"."main_staging"."stg_yellow_trips"
where total_amount is null



  
  
      
    ) dbt_internal_test

    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_revenue
from "de_pipeline"."main_marts"."mart_daily_revenue"
where total_revenue is null



  
  
      
    ) dbt_internal_test
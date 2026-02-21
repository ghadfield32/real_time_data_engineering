
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select date_key
from "de_pipeline"."main_marts"."dim_dates"
where date_key is null



  
  
      
    ) dbt_internal_test
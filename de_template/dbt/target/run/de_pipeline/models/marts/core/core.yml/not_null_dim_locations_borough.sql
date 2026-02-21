
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select borough
from "de_pipeline"."main_marts"."dim_locations"
where borough is null



  
  
      
    ) dbt_internal_test
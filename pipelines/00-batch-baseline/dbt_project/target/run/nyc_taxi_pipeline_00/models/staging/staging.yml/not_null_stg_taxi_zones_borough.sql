
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select borough
from "dev"."main"."stg_taxi_zones"
where borough is null



  
  
      
    ) dbt_internal_test
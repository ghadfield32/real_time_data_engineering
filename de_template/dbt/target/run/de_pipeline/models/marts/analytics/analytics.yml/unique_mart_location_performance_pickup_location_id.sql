
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    pickup_location_id as unique_field,
    count(*) as n_records

from "de_pipeline"."main_marts"."mart_location_performance"
where pickup_location_id is not null
group by pickup_location_id
having count(*) > 1



  
  
      
    ) dbt_internal_test
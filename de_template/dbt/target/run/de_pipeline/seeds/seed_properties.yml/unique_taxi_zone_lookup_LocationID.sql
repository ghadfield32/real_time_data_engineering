
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    LocationID as unique_field,
    count(*) as n_records

from "de_pipeline"."main_raw"."taxi_zone_lookup"
where LocationID is not null
group by LocationID
having count(*) > 1



  
  
      
    ) dbt_internal_test
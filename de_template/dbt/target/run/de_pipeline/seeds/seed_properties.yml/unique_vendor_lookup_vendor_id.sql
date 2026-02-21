
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    vendor_id as unique_field,
    count(*) as n_records

from "de_pipeline"."main_raw"."vendor_lookup"
where vendor_id is not null
group by vendor_id
having count(*) > 1



  
  
      
    ) dbt_internal_test
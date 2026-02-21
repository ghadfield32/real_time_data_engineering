
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    vendor_abbr as unique_field,
    count(*) as n_records

from "de_pipeline"."main_raw"."vendor_lookup"
where vendor_abbr is not null
group by vendor_abbr
having count(*) > 1



  
  
      
    ) dbt_internal_test
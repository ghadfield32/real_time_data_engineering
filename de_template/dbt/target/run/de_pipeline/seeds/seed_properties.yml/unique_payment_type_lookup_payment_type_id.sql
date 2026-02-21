
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    payment_type_id as unique_field,
    count(*) as n_records

from "de_pipeline"."main_raw"."payment_type_lookup"
where payment_type_id is not null
group by payment_type_id
having count(*) > 1



  
  
      
    ) dbt_internal_test
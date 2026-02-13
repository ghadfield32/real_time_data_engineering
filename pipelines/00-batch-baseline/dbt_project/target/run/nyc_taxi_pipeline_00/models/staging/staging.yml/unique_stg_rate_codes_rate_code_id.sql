
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    rate_code_id as unique_field,
    count(*) as n_records

from "dev"."main"."stg_rate_codes"
where rate_code_id is not null
group by rate_code_id
having count(*) > 1



  
  
      
    ) dbt_internal_test
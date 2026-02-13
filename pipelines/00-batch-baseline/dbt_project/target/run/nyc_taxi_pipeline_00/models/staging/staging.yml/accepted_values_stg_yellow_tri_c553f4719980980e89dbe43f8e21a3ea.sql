
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payment_type_id as value_field,
        count(*) as n_records

    from "dev"."main"."stg_yellow_trips"
    group by payment_type_id

)

select *
from all_values
where value_field not in (
    '0','1','2','3','4','5','6'
)



  
  
      
    ) dbt_internal_test
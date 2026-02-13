
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  /*
    Singular test: fare_amount should not exceed total_amount.
*/

select
    trip_id,
    fare_amount,
    total_amount
from "dev"."main"."stg_yellow_trips"
where fare_amount > total_amount + 0.01
  and total_amount > 0
  
  
      
    ) dbt_internal_test
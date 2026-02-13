
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  /*
    Singular test: No trip should have negative duration.
*/

select
    trip_id,
    pickup_datetime,
    dropoff_datetime,
    trip_duration_minutes
from "dev"."main"."int_trip_metrics"
where trip_duration_minutes < 0
  
  
      
    ) dbt_internal_test
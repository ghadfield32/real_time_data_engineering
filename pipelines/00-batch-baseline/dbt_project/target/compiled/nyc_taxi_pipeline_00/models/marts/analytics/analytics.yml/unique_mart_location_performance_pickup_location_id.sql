
    
    

select
    pickup_location_id as unique_field,
    count(*) as n_records

from "dev"."main"."mart_location_performance"
where pickup_location_id is not null
group by pickup_location_id
having count(*) > 1




    
    

select
    location_id as unique_field,
    count(*) as n_records

from "de_pipeline"."main_staging"."stg_taxi_zones"
where location_id is not null
group by location_id
having count(*) > 1



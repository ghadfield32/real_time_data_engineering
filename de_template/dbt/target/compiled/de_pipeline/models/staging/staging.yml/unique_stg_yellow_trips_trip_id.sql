
    
    

select
    trip_id as unique_field,
    count(*) as n_records

from "de_pipeline"."main_staging"."stg_yellow_trips"
where trip_id is not null
group by trip_id
having count(*) > 1



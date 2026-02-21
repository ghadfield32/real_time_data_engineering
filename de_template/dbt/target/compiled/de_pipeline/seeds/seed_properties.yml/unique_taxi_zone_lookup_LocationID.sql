
    
    

select
    LocationID as unique_field,
    count(*) as n_records

from "de_pipeline"."main_raw"."taxi_zone_lookup"
where LocationID is not null
group by LocationID
having count(*) > 1




    
    

select
    vendor_id as unique_field,
    count(*) as n_records

from "de_pipeline"."main_raw"."vendor_lookup"
where vendor_id is not null
group by vendor_id
having count(*) > 1



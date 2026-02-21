
    
    

select
    vendor_abbr as unique_field,
    count(*) as n_records

from "de_pipeline"."main_raw"."vendor_lookup"
where vendor_abbr is not null
group by vendor_abbr
having count(*) > 1



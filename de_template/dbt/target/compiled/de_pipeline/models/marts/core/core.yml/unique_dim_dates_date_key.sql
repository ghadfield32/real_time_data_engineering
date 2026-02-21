
    
    

select
    date_key as unique_field,
    count(*) as n_records

from "de_pipeline"."main_marts"."dim_dates"
where date_key is not null
group by date_key
having count(*) > 1



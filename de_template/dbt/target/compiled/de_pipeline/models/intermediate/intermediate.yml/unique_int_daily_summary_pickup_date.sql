
    
    

select
    pickup_date as unique_field,
    count(*) as n_records

from "de_pipeline"."main_intermediate"."int_daily_summary"
where pickup_date is not null
group by pickup_date
having count(*) > 1



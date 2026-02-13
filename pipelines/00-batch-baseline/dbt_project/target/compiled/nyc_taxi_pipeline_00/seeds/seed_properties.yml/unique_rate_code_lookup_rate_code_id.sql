
    
    

select
    rate_code_id as unique_field,
    count(*) as n_records

from "dev"."main"."rate_code_lookup"
where rate_code_id is not null
group by rate_code_id
having count(*) > 1



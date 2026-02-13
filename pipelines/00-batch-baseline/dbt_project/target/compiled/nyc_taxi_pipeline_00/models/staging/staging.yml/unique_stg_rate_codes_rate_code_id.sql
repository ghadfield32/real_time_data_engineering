
    
    

select
    rate_code_id as unique_field,
    count(*) as n_records

from "dev"."main"."stg_rate_codes"
where rate_code_id is not null
group by rate_code_id
having count(*) > 1




    
    

select
    payment_type_id as unique_field,
    count(*) as n_records

from "de_pipeline"."main_marts"."dim_payment_types"
where payment_type_id is not null
group by payment_type_id
having count(*) > 1



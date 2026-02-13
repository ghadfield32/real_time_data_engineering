
    
    

select
    payment_type_id as unique_field,
    count(*) as n_records

from "dev"."main"."dim_payment_types"
where payment_type_id is not null
group by payment_type_id
having count(*) > 1



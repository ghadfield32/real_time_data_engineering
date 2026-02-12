/*
    Dimension table: Payment type descriptions.
*/

with payment_types as (
    select * from {{ ref('stg_payment_types') }}
),

final as (
    select
        payment_type_id,
        payment_type_name
    from payment_types
)

select * from final

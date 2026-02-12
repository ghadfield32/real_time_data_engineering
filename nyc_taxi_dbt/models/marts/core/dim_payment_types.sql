/*
    Dimension table: Payment type descriptions.

    Maps payment_type_id to human-readable names.
    Sourced from the payment_type_lookup seed via staging.
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

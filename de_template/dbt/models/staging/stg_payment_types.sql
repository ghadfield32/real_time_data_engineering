/*
    Staging model: Payment type lookup
    Maps payment_type_id to human-readable names.
*/

with source as (
    select * from {{ ref('payment_type_lookup') }}
),

renamed as (
    select
        payment_type_id,
        payment_type_name
    from source
)

select * from renamed

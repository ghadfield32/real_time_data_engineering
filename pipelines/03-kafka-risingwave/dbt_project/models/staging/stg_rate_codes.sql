/*
    Staging model: Rate code lookup
    Maps rate_code_id to human-readable names.
*/

with source as (
    select * from {{ ref('rate_code_lookup') }}
),

renamed as (
    select
        rate_code_id,
        rate_code_name
    from source
)

select * from renamed

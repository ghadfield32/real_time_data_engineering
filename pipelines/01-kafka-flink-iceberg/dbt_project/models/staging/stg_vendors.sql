/*
    Staging model: Vendor lookup
    Maps vendor_id to vendor name and abbreviation.
*/

with source as (
    select * from {{ ref('vendor_lookup') }}
),

renamed as (
    select
        vendor_id,
        vendor_name,
        vendor_abbr
    from source
)

select * from renamed

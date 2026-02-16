/*
    Dimension table: Taxi vendor descriptions.
    TPEP provider: 1=Creative Mobile Technologies (CMT), 2=VeriFone Inc. (VFI)
*/

with vendors as (
    select * from {{ ref('stg_vendors') }}
),

final as (
    select
        vendor_id,
        vendor_name,
        vendor_abbr
    from vendors
)

select * from final

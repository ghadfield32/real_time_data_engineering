/*
    Dimension table: TLC Taxi Zone locations.

    Maps location IDs to borough, zone name, and service zone.
    Sourced from the taxi_zone_lookup seed via staging.
*/

with zones as (
    select * from {{ ref('stg_taxi_zones') }}
),

final as (
    select
        location_id,
        borough,
        zone_name,
        service_zone
    from zones
)

select * from final

/*
    Dimension table: TLC Taxi Zone locations.
*/

with zones as (
    select * from "de_pipeline"."main_staging"."stg_taxi_zones"
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
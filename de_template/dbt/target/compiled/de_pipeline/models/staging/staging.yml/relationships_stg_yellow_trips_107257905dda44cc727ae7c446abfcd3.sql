
    
    

with child as (
    select pickup_location_id as from_field
    from "de_pipeline"."main_staging"."stg_yellow_trips"
    where pickup_location_id is not null
),

parent as (
    select location_id as to_field
    from "de_pipeline"."main_staging"."stg_taxi_zones"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



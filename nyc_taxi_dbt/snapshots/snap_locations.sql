/*
    Snapshot: SCD Type 2 for taxi zone locations.

    Tracks changes to borough/zone name mappings over time.
    In practice, taxi zone boundaries rarely change, but this
    demonstrates dbt's snapshot (slowly changing dimension) capability.

    Strategy: check - compares all tracked columns for changes.
    If borough or zone_name changes, the old record gets dbt_valid_to
    set and a new record is inserted.
*/

{% snapshot snap_locations %}

{{
  config(
    target_schema='snapshots',
    unique_key='location_id',
    strategy='check',
    check_cols=['borough', 'zone_name', 'service_zone']
  )
}}

select * from {{ ref('stg_taxi_zones') }}

{% endsnapshot %}


  
    
    

    create  table
      "de_pipeline"."main_staging"."stg_yellow_trips__dbt_tmp"
  
    as (
      

with source as (
    select * from iceberg_scan('s3://warehouse/silver/cleaned_trips', allow_moved_paths = true)
),

final as (
    select
        -- Flink already generated the surrogate key
        trip_id,

        -- identifiers (already renamed and cast by Flink)
        vendor_id,
        rate_code_id,
        pickup_location_id,
        dropoff_location_id,
        payment_type_id,

        -- timestamps (already parsed by Flink)
        cast(pickup_datetime as timestamp) as pickup_datetime,
        cast(dropoff_datetime as timestamp) as dropoff_datetime,

        -- trip info
        passenger_count,
        trip_distance_miles,
        store_and_fwd_flag,

        -- financials (already rounded by Flink)
        round(cast(fare_amount as decimal(10, 2)), 2) as fare_amount,
        round(cast(extra_amount as decimal(10, 2)), 2) as extra_amount,
        round(cast(mta_tax as decimal(10, 2)), 2) as mta_tax,
        round(cast(tip_amount as decimal(10, 2)), 2) as tip_amount,
        round(cast(tolls_amount as decimal(10, 2)), 2) as tolls_amount,
        round(cast(improvement_surcharge as decimal(10, 2)), 2) as improvement_surcharge,
        round(cast(total_amount as decimal(10, 2)), 2) as total_amount,
        round(cast(congestion_surcharge as decimal(10, 2)), 2) as congestion_surcharge,
        round(cast(airport_fee as decimal(10, 2)), 2) as airport_fee

    from source
    -- Flink already applied quality filters; this is a safety net
    where pickup_datetime is not null
      and dropoff_datetime is not null
)

select * from final
    );
  
  
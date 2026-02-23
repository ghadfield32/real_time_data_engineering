{#
    Staging model: Yellow taxi trip records (Iceberg pipeline variant)

    This is a simple passthrough since Flink already performed the heavy lifting:
      - Column renaming (VendorID -> vendor_id, etc.)
      - Type casting
      - Data quality filtering (nulls, negative fares, date range)
      - Surrogate key generation (MD5 hash)

    The source reads the Silver Iceberg table via DuckDB iceberg_scan().
#}

with source as (
    select * from {{ source('raw_nyc_taxi', 'raw_yellow_trips') }}
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

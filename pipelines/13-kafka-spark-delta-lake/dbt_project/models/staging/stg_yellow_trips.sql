{#
    Staging model: Yellow taxi trip records — Pipeline 13 (Delta Lake)

    NOTE: This model differs from other pipelines (P01/P04/P07/etc.) because
    Spark's silver_transform.py already renames all columns to snake_case and
    computes trip_id before writing to the Silver Delta Lake table. The source
    for this pipeline is delta_scan('s3://warehouse/silver/cleaned_trips') which
    points to that already-transformed Silver table.

    Column mapping difference vs Flink-based pipelines:
      Flink Silver (P01):  VendorID, tpep_pickup_datetime, PULocationID, ...  (original names)
      Spark Silver (P13):  vendor_id, pickup_datetime, pickup_location_id, ...  (snake_case)

    trip_id: Spark generates this during silver_transform using the same MD5/concat_ws
    logic as dbt_utils.generate_surrogate_key so values are consistent across pipelines.
    We pass it through directly rather than recomputing with renamed column names.
#}

with source as (
    select * from {{ source('raw_nyc_taxi', 'raw_yellow_trips') }}
),

renamed as (
    select
        -- surrogate key: already computed by Spark silver_transform.py
        -- md5(concat_ws('|', VendorID, tpep_pickup_datetime, ...)) before renaming
        -- value is identical to what generate_surrogate_key would produce on the
        -- original Parquet column names, so trip_id is consistent across pipelines
        trip_id,

        -- identifiers (already cast by Spark, confirm types here)
        cast(vendor_id as integer)           as vendor_id,
        cast(rate_code_id as integer)        as rate_code_id,
        cast(pickup_location_id as integer)  as pickup_location_id,
        cast(dropoff_location_id as integer) as dropoff_location_id,
        cast(payment_type as integer)        as payment_type_id,

        -- timestamps (already parsed by Spark)
        cast(pickup_datetime as timestamp)  as pickup_datetime,
        cast(dropoff_datetime as timestamp) as dropoff_datetime,

        -- trip info
        cast(passenger_count as integer)        as passenger_count,
        cast(trip_distance_miles as double)     as trip_distance_miles,
        store_and_fwd_flag,

        -- financials (already rounded by Spark)
        round(cast(fare_amount as decimal(10, 2)), 2)             as fare_amount,
        round(cast(extra as decimal(10, 2)), 2)                   as extra_amount,
        round(cast(mta_tax as decimal(10, 2)), 2)                 as mta_tax,
        round(cast(tip_amount as decimal(10, 2)), 2)              as tip_amount,
        round(cast(tolls_amount as decimal(10, 2)), 2)            as tolls_amount,
        round(cast(improvement_surcharge as decimal(10, 2)), 2)   as improvement_surcharge,
        round(cast(total_amount as decimal(10, 2)), 2)            as total_amount,
        round(cast(congestion_surcharge as decimal(10, 2)), 2)    as congestion_surcharge,
        round(cast(airport_fee as decimal(10, 2)), 2)             as airport_fee

    from source
    where pickup_datetime is not null
      and dropoff_datetime is not null
      and trip_distance_miles >= 0
      and fare_amount >= 0
      -- date range filter (consistent with other pipelines)
      and cast(pickup_datetime as date) >= date '2024-01-01'
      and cast(pickup_datetime as date) < date '2024-02-01'
)

select * from renamed



with source as (
    select * from read_parquet('/data/yellow_tripdata_2024-01.parquet')
),

renamed as (
    select
        -- surrogate key (MD5 hash of composite key)
        md5(cast(coalesce(cast(VendorID as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(tpep_pickup_datetime as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(tpep_dropoff_datetime as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(PULocationID as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(DOLocationID as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(fare_amount as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(total_amount as TEXT), '_dbt_utils_surrogate_key_null_') as TEXT)) as trip_id,

        -- identifiers
        cast("VendorID" as integer) as vendor_id,
        cast("RatecodeID" as integer) as rate_code_id,
        cast("PULocationID" as integer) as pickup_location_id,
        cast("DOLocationID" as integer) as dropoff_location_id,
        cast(payment_type as integer) as payment_type_id,

        -- timestamps
        cast(tpep_pickup_datetime as timestamp) as pickup_datetime,
        cast(tpep_dropoff_datetime as timestamp) as dropoff_datetime,

        -- trip info
        cast(passenger_count as integer) as passenger_count,
        cast(trip_distance as double) as trip_distance_miles,
        store_and_fwd_flag,

        -- financials
        round(cast(fare_amount as decimal(10, 2)), 2) as fare_amount,
        round(cast(extra as decimal(10, 2)), 2) as extra_amount,
        round(cast(mta_tax as decimal(10, 2)), 2) as mta_tax,
        round(cast(tip_amount as decimal(10, 2)), 2) as tip_amount,
        round(cast(tolls_amount as decimal(10, 2)), 2) as tolls_amount,
        round(cast(improvement_surcharge as decimal(10, 2)), 2) as improvement_surcharge,
        round(cast(total_amount as decimal(10, 2)), 2) as total_amount,
        round(cast(congestion_surcharge as decimal(10, 2)), 2) as congestion_surcharge,
        round(cast(Airport_fee as decimal(10, 2)), 2) as airport_fee

    from source
    where tpep_pickup_datetime is not null
      and tpep_dropoff_datetime is not null
      and trip_distance >= 0
      and fare_amount >= 0
      -- filter out-of-range dates (data quality: ~18 trips outside Jan 2024)
      and cast(tpep_pickup_datetime as date) >= date '2024-01-01'
      and cast(tpep_pickup_datetime as date) < date '2024-02-01'
)

select * from renamed
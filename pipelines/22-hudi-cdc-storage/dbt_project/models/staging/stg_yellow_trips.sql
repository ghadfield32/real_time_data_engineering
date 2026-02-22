{#
    Staging model: Yellow taxi trip records (Hudi Silver)

    P22 reads from the Silver Hudi table written by Spark (silver_transform.py).
    Spark has already renamed columns to snake_case and computed trip_id, so this
    model maps Silver column names to the canonical staging schema expected by
    intermediate and mart models.

    Silver column names (from Spark):
        trip_id, vendor_id, pickup_datetime, dropoff_datetime, passenger_count,
        trip_distance_miles, rate_code_id, store_and_fwd_flag,
        pickup_location_id, dropoff_location_id, payment_type,
        fare_amount, extra, mta_tax, tip_amount, tolls_amount,
        improvement_surcharge, total_amount, congestion_surcharge, airport_fee
#}

with source as (
    select * from {{ source('raw_nyc_taxi', 'raw_yellow_trips') }}
),

renamed as (
    select
        -- surrogate key (pre-computed by Spark Silver transform)
        trip_id,

        -- identifiers
        vendor_id,
        rate_code_id,
        pickup_location_id,
        dropoff_location_id,
        cast(payment_type as integer) as payment_type_id,

        -- timestamps (already parsed to timestamp by Spark)
        pickup_datetime,
        dropoff_datetime,

        -- trip info
        cast(passenger_count as integer) as passenger_count,
        trip_distance_miles,
        store_and_fwd_flag,

        -- financials
        fare_amount,
        round(cast(extra as decimal(10, 2)), 2) as extra_amount,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        total_amount,
        congestion_surcharge,
        airport_fee

    from source
    where pickup_datetime is not null
      and pickup_datetime >= timestamp '2024-01-01'
      and pickup_datetime < timestamp '2024-02-01'
)

select * from renamed

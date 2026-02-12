-- Pipeline 03: Bronze materialized view
-- Minimal transformation: rename columns, cast timestamps.
-- This MV updates automatically as Kafka events arrive.

CREATE MATERIALIZED VIEW IF NOT EXISTS bronze_raw_trips AS
SELECT
    "VendorID" AS vendor_id,
    tpep_pickup_datetime::TIMESTAMP AS pickup_datetime,
    tpep_dropoff_datetime::TIMESTAMP AS dropoff_datetime,
    passenger_count,
    trip_distance,
    "RatecodeID" AS rate_code_id,
    store_and_fwd_flag,
    "PULocationID" AS pickup_location_id,
    "DOLocationID" AS dropoff_location_id,
    payment_type AS payment_type_id,
    fare_amount,
    extra AS extra_amount,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    congestion_surcharge,
    "Airport_fee" AS airport_fee
FROM taxi_raw_source;

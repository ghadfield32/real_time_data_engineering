-- Pipeline 14: Bronze materialized view
-- Minimal transformation: parse JSON text, rename columns, cast types.
-- This MV updates automatically as Kafka events arrive.

CREATE MATERIALIZED VIEW IF NOT EXISTS bronze_raw_trips AS
SELECT
    (data->>'VendorID')::BIGINT           AS vendor_id,
    (data->>'tpep_pickup_datetime')::TIMESTAMP  AS pickup_datetime,
    (data->>'tpep_dropoff_datetime')::TIMESTAMP AS dropoff_datetime,
    (data->>'passenger_count')::BIGINT    AS passenger_count,
    (data->>'trip_distance')::DOUBLE PRECISION AS trip_distance,
    (data->>'RatecodeID')::BIGINT         AS rate_code_id,
    data->>'store_and_fwd_flag'           AS store_and_fwd_flag,
    (data->>'PULocationID')::BIGINT       AS pickup_location_id,
    (data->>'DOLocationID')::BIGINT       AS dropoff_location_id,
    (data->>'payment_type')::BIGINT       AS payment_type_id,
    (data->>'fare_amount')::DOUBLE PRECISION    AS fare_amount,
    (data->>'extra')::DOUBLE PRECISION          AS extra_amount,
    (data->>'mta_tax')::DOUBLE PRECISION        AS mta_tax,
    (data->>'tip_amount')::DOUBLE PRECISION     AS tip_amount,
    (data->>'tolls_amount')::DOUBLE PRECISION   AS tolls_amount,
    (data->>'improvement_surcharge')::DOUBLE PRECISION AS improvement_surcharge,
    (data->>'total_amount')::DOUBLE PRECISION   AS total_amount,
    (data->>'congestion_surcharge')::DOUBLE PRECISION  AS congestion_surcharge,
    (data->>'Airport_fee')::DOUBLE PRECISION    AS airport_fee
FROM (
    SELECT text::JSONB AS data FROM taxi_source
);

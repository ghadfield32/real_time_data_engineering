-- ClickHouse tables for NYC Taxi Gold layer
-- Loaded from dbt mart output (parquet/CSV)

CREATE DATABASE IF NOT EXISTS nyc_taxi;

-- Fact table: trips
CREATE TABLE IF NOT EXISTS nyc_taxi.fct_trips (
    trip_id String,
    vendor_id Int32,
    rate_code_id Int32,
    pickup_location_id Int32,
    dropoff_location_id Int32,
    payment_type_id Int32,
    pickup_datetime DateTime,
    dropoff_datetime DateTime,
    passenger_count Int32,
    trip_distance_miles Float64,
    fare_amount Decimal(10, 2),
    extra_amount Decimal(10, 2),
    mta_tax Decimal(10, 2),
    tip_amount Decimal(10, 2),
    tolls_amount Decimal(10, 2),
    improvement_surcharge Decimal(10, 2),
    total_amount Decimal(10, 2),
    congestion_surcharge Decimal(10, 2),
    airport_fee Decimal(10, 2),
    trip_duration_minutes Int64,
    avg_speed_mph Float64,
    cost_per_mile Float64,
    tip_percentage Float64,
    pickup_date Date,
    pickup_hour Int32,
    is_weekend UInt8
) ENGINE = MergeTree()
ORDER BY (pickup_datetime, pickup_location_id, vendor_id)
PARTITION BY toYYYYMM(pickup_datetime);

-- Mart: daily revenue
CREATE TABLE IF NOT EXISTS nyc_taxi.mart_daily_revenue (
    revenue_date Date,
    total_trips Int64,
    total_revenue Decimal(12, 2),
    total_fare Decimal(12, 2),
    total_tips Decimal(12, 2),
    total_tolls Decimal(12, 2),
    avg_trip_distance Float64,
    avg_trip_duration Float64,
    avg_fare Float64,
    avg_tip_percentage Float64
) ENGINE = MergeTree()
ORDER BY revenue_date;

-- Mart: location performance
CREATE TABLE IF NOT EXISTS nyc_taxi.mart_location_performance (
    pickup_location_id Int32,
    zone_name String,
    borough String,
    total_trips Int64,
    total_revenue Decimal(12, 2),
    avg_fare Decimal(10, 2),
    avg_trip_distance Float64,
    avg_trip_duration Float64,
    avg_tip_percentage Float64
) ENGINE = MergeTree()
ORDER BY (borough, total_trips);

-- Mart: hourly demand
CREATE TABLE IF NOT EXISTS nyc_taxi.mart_hourly_demand (
    pickup_hour Int32,
    day_of_week String,
    total_trips Int64,
    avg_trip_distance Float64,
    avg_fare Decimal(10, 2),
    avg_duration Float64,
    peak_indicator String
) ENGINE = MergeTree()
ORDER BY (pickup_hour, day_of_week);

-- Dimension: locations
CREATE TABLE IF NOT EXISTS nyc_taxi.dim_locations (
    location_id Int32,
    borough String,
    zone_name String,
    service_zone String
) ENGINE = MergeTree()
ORDER BY location_id;

-- Dimension: payment types
CREATE TABLE IF NOT EXISTS nyc_taxi.dim_payment_types (
    payment_type_id Int32,
    payment_description String
) ENGINE = MergeTree()
ORDER BY payment_type_id;

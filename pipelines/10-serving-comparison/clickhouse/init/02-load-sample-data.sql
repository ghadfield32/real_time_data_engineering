-- Load data from source parquet file and seed CSVs into ClickHouse tables
-- This replicates the dbt Gold layer transformations directly in ClickHouse SQL

-- ============================================================
-- 1. Load dimension: payment types (seed data)
-- ============================================================
INSERT INTO nyc_taxi.dim_payment_types VALUES
    (1, 'Credit card'), (2, 'Cash'), (3, 'No charge'),
    (4, 'Dispute'), (5, 'Unknown'), (6, 'Voided trip');

-- ============================================================
-- 2. Load dimension: locations (from taxi_zone_lookup.csv)
-- ============================================================
INSERT INTO nyc_taxi.dim_locations
SELECT
    LocationID AS location_id,
    Borough AS borough,
    Zone AS zone_name,
    service_zone
FROM file('/var/lib/clickhouse/user_files/seeds/taxi_zone_lookup.csv', 'CSVWithNames',
    'LocationID Int32, Borough String, Zone String, service_zone String');

-- ============================================================
-- 3. Load fact table from raw parquet (with transformations)
-- ============================================================
INSERT INTO nyc_taxi.fct_trips
SELECT
    MD5(concat(
        toString(VendorID), '|',
        toString(tpep_pickup_datetime), '|',
        toString(tpep_dropoff_datetime), '|',
        toString(PULocationID), '|',
        toString(DOLocationID), '|',
        toString(fare_amount), '|',
        toString(total_amount)
    )) AS trip_id,
    toInt32(VendorID) AS vendor_id,
    toInt32(RatecodeID) AS rate_code_id,
    toInt32(PULocationID) AS pickup_location_id,
    toInt32(DOLocationID) AS dropoff_location_id,
    toInt32(payment_type) AS payment_type_id,
    tpep_pickup_datetime AS pickup_datetime,
    tpep_dropoff_datetime AS dropoff_datetime,
    toInt32(passenger_count) AS passenger_count,
    trip_distance AS trip_distance_miles,
    toDecimal64(fare_amount, 2) AS fare_amount,
    toDecimal64(extra, 2) AS extra_amount,
    toDecimal64(mta_tax, 2) AS mta_tax,
    toDecimal64(tip_amount, 2) AS tip_amount,
    toDecimal64(tolls_amount, 2) AS tolls_amount,
    toDecimal64(improvement_surcharge, 2) AS improvement_surcharge,
    toDecimal64(total_amount, 2) AS total_amount,
    toDecimal64(congestion_surcharge, 2) AS congestion_surcharge,
    toDecimal64(Airport_fee, 2) AS airport_fee,
    toInt64(dateDiff('minute', tpep_pickup_datetime, tpep_dropoff_datetime)) AS trip_duration_minutes,
    if(dateDiff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) > 0,
       trip_distance / (dateDiff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) / 60.0),
       0) AS avg_speed_mph,
    if(trip_distance > 0, toFloat64(fare_amount) / trip_distance, 0) AS cost_per_mile,
    if(toFloat64(fare_amount) > 0, toFloat64(tip_amount) / toFloat64(fare_amount) * 100, 0) AS tip_percentage,
    toDate(tpep_pickup_datetime) AS pickup_date,
    toInt32(toHour(tpep_pickup_datetime)) AS pickup_hour,
    toUInt8(toDayOfWeek(tpep_pickup_datetime) >= 6) AS is_weekend
FROM file('/var/lib/clickhouse/user_files/source-data/yellow_tripdata_2024-01.parquet', 'Parquet')
WHERE fare_amount >= 0
  AND total_amount >= 0
  AND trip_distance >= 0
  AND passenger_count > 0
  AND tpep_pickup_datetime >= '2024-01-01'
  AND tpep_pickup_datetime < '2024-02-01';

-- ============================================================
-- 4. Populate mart: daily revenue
-- ============================================================
INSERT INTO nyc_taxi.mart_daily_revenue
SELECT
    pickup_date AS revenue_date,
    count() AS total_trips,
    sum(total_amount) AS total_revenue,
    sum(fare_amount) AS total_fare,
    sum(tip_amount) AS total_tips,
    sum(tolls_amount) AS total_tolls,
    avg(trip_distance_miles) AS avg_trip_distance,
    avg(trip_duration_minutes) AS avg_trip_duration,
    avg(fare_amount) AS avg_fare,
    avg(tip_percentage) AS avg_tip_percentage
FROM nyc_taxi.fct_trips
GROUP BY pickup_date
ORDER BY pickup_date;

-- ============================================================
-- 5. Populate mart: location performance
-- ============================================================
INSERT INTO nyc_taxi.mart_location_performance
SELECT
    f.pickup_location_id,
    coalesce(d.zone_name, 'Unknown') AS zone_name,
    coalesce(d.borough, 'Unknown') AS borough,
    count() AS total_trips,
    sum(f.total_amount) AS total_revenue,
    avg(f.fare_amount) AS avg_fare,
    avg(f.trip_distance_miles) AS avg_trip_distance,
    avg(f.trip_duration_minutes) AS avg_trip_duration,
    avg(f.tip_percentage) AS avg_tip_percentage
FROM nyc_taxi.fct_trips f
LEFT JOIN nyc_taxi.dim_locations d ON f.pickup_location_id = d.location_id
GROUP BY f.pickup_location_id, d.zone_name, d.borough;

-- ============================================================
-- 6. Populate mart: hourly demand
-- ============================================================
INSERT INTO nyc_taxi.mart_hourly_demand
SELECT
    pickup_hour,
    multiIf(
        toDayOfWeek(pickup_date) = 1, 'Monday',
        toDayOfWeek(pickup_date) = 2, 'Tuesday',
        toDayOfWeek(pickup_date) = 3, 'Wednesday',
        toDayOfWeek(pickup_date) = 4, 'Thursday',
        toDayOfWeek(pickup_date) = 5, 'Friday',
        toDayOfWeek(pickup_date) = 6, 'Saturday',
        'Sunday'
    ) AS day_of_week,
    count() AS total_trips,
    avg(trip_distance_miles) AS avg_trip_distance,
    avg(fare_amount) AS avg_fare,
    avg(trip_duration_minutes) AS avg_duration,
    if(count() > 10000, 'High', if(count() > 5000, 'Medium', 'Low')) AS peak_indicator
FROM nyc_taxi.fct_trips
GROUP BY pickup_hour, toDayOfWeek(pickup_date)
ORDER BY pickup_hour, toDayOfWeek(pickup_date);

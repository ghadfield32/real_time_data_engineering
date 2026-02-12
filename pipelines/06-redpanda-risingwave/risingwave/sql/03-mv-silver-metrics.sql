-- Pipeline 06: Silver materialized view
-- Full cleaning + enrichment (equivalent to stg_yellow_trips + int_trip_metrics).
-- Applies quality filters, computes metrics, adds time dimensions.
-- This MV updates automatically as Redpanda events arrive.

CREATE MATERIALIZED VIEW IF NOT EXISTS silver_cleaned_trips AS
WITH cleaned AS (
    SELECT
        -- Surrogate key
        md5(concat_ws('|',
            vendor_id::TEXT,
            pickup_datetime::TEXT,
            dropoff_datetime::TEXT,
            pickup_location_id::TEXT,
            dropoff_location_id::TEXT,
            fare_amount::TEXT,
            total_amount::TEXT
        )) AS trip_id,

        -- Identifiers (cast to proper types)
        vendor_id::INTEGER AS vendor_id,
        rate_code_id::INTEGER AS rate_code_id,
        pickup_location_id::INTEGER AS pickup_location_id,
        dropoff_location_id::INTEGER AS dropoff_location_id,
        payment_type_id::INTEGER AS payment_type_id,

        -- Timestamps
        pickup_datetime,
        dropoff_datetime,

        -- Trip info
        passenger_count::INTEGER AS passenger_count,
        trip_distance::DOUBLE PRECISION AS trip_distance_miles,
        store_and_fwd_flag,

        -- Financials (cast to NUMERIC for precision)
        ROUND(fare_amount::NUMERIC(10,2), 2) AS fare_amount,
        ROUND(extra_amount::NUMERIC(10,2), 2) AS extra_amount,
        ROUND(mta_tax::NUMERIC(10,2), 2) AS mta_tax,
        ROUND(tip_amount::NUMERIC(10,2), 2) AS tip_amount,
        ROUND(tolls_amount::NUMERIC(10,2), 2) AS tolls_amount,
        ROUND(improvement_surcharge::NUMERIC(10,2), 2) AS improvement_surcharge,
        ROUND(total_amount::NUMERIC(10,2), 2) AS total_amount,
        ROUND(congestion_surcharge::NUMERIC(10,2), 2) AS congestion_surcharge,
        ROUND(airport_fee::NUMERIC(10,2), 2) AS airport_fee,

        -- Computed: duration in minutes
        (EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime)) / 60)::BIGINT
            AS trip_duration_minutes,

        -- Computed: average speed (mph)
        CASE
            WHEN (EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime)) / 60) > 0
            THEN ROUND(
                (trip_distance / ((EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime)) / 60) / 60.0))::NUMERIC,
                2
            )::DOUBLE PRECISION
            ELSE NULL
        END AS avg_speed_mph,

        -- Computed: cost per mile
        CASE
            WHEN trip_distance > 0
            THEN ROUND((fare_amount / trip_distance)::NUMERIC, 2)::DOUBLE PRECISION
            ELSE NULL
        END AS cost_per_mile,

        -- Computed: tip percentage
        CASE
            WHEN fare_amount > 0
            THEN ROUND(((tip_amount / fare_amount) * 100)::NUMERIC, 2)::DOUBLE PRECISION
            ELSE NULL
        END AS tip_percentage,

        -- Time dimensions
        pickup_datetime::DATE AS pickup_date,
        EXTRACT(HOUR FROM pickup_datetime)::BIGINT AS pickup_hour,
        trim(to_char(pickup_datetime, 'Day')) AS pickup_day_of_week,
        CASE
            WHEN EXTRACT(DOW FROM pickup_datetime) IN (0, 6) THEN true
            ELSE false
        END AS is_weekend

    FROM bronze_raw_trips
    WHERE
        -- Quality filters: no nulls for key fields
        pickup_datetime IS NOT NULL
        AND dropoff_datetime IS NOT NULL
        AND trip_distance >= 0
        AND fare_amount >= 0
        -- Date range: January 2024 only
        AND pickup_datetime::DATE >= DATE '2024-01-01'
        AND pickup_datetime::DATE < DATE '2024-02-01'
)

SELECT *
FROM cleaned
WHERE
    -- Filter impossible trips
    trip_duration_minutes BETWEEN 1 AND 720
    AND (avg_speed_mph IS NULL OR avg_speed_mph < 100);

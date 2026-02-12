-- Benchmark Query 1: Daily Revenue for January 2024
SELECT
    pickup_date AS revenue_date,
    count() AS total_trips,
    sum(total_amount) AS total_revenue,
    sum(fare_amount) AS total_fare,
    sum(tip_amount) AS total_tips,
    avg(trip_distance_miles) AS avg_distance,
    avg(trip_duration_minutes) AS avg_duration
FROM nyc_taxi.fct_trips
WHERE pickup_date BETWEEN '2024-01-01' AND '2024-01-31'
GROUP BY pickup_date
ORDER BY pickup_date;

-- Benchmark Query 3: Hourly Demand Heatmap
SELECT
    pickup_hour,
    toDayOfWeek(pickup_date) AS day_of_week,
    count() AS total_trips,
    avg(trip_distance_miles) AS avg_distance,
    avg(fare_amount) AS avg_fare,
    avg(trip_duration_minutes) AS avg_duration
FROM nyc_taxi.fct_trips
GROUP BY pickup_hour, day_of_week
ORDER BY day_of_week, pickup_hour;

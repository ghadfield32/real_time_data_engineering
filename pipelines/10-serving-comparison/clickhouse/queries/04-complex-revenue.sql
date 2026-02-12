-- Benchmark Query 4: Revenue by Payment Type per Borough per Weekday
SELECT
    d.borough,
    p.payment_description,
    if(f.is_weekend = 1, 'Weekend', 'Weekday') AS day_type,
    count() AS trip_count,
    sum(f.total_amount) AS total_revenue,
    avg(f.fare_amount) AS avg_fare,
    avg(f.tip_percentage) AS avg_tip_pct
FROM nyc_taxi.fct_trips f
LEFT JOIN nyc_taxi.dim_locations d ON f.pickup_location_id = d.location_id
LEFT JOIN nyc_taxi.dim_payment_types p ON f.payment_type_id = p.payment_type_id
GROUP BY d.borough, p.payment_description, day_type
ORDER BY d.borough, total_revenue DESC;

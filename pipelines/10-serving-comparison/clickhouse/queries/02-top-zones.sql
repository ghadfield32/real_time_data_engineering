-- Benchmark Query 2: Top 10 Pickup Zones by Revenue
SELECT
    f.pickup_location_id,
    d.zone_name,
    d.borough,
    count() AS total_trips,
    sum(f.total_amount) AS total_revenue,
    avg(f.fare_amount) AS avg_fare,
    avg(f.tip_percentage) AS avg_tip_pct
FROM nyc_taxi.fct_trips f
LEFT JOIN nyc_taxi.dim_locations d ON f.pickup_location_id = d.location_id
GROUP BY f.pickup_location_id, d.zone_name, d.borough
ORDER BY total_revenue DESC
LIMIT 10;

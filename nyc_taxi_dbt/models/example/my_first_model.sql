/*
    Week 1 - Your first dbt model!

    This model creates a simple table with hardcoded data.
    It demonstrates the basics of dbt: SQL files in the models/ folder
    are compiled and run against your data warehouse (DuckDB).

    Try running: uv run dbt run --profiles-dir .
*/

select
    1 as trip_id,
    'yellow' as taxi_type,
    12.50 as fare_amount,
    timestamp '2024-01-15 08:30:00' as pickup_datetime
union all
select
    2 as trip_id,
    'yellow' as taxi_type,
    8.75 as fare_amount,
    timestamp '2024-01-15 14:15:00' as pickup_datetime
union all
select
    3 as trip_id,
    'yellow' as taxi_type,
    25.00 as fare_amount,
    timestamp '2024-01-16 19:45:00' as pickup_datetime

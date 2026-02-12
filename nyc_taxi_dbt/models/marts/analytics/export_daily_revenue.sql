/*
    External materialization: Export daily revenue to parquet.

    Demonstrates dbt-duckdb's 'external' materialization, which writes
    model output to a parquet file on disk instead of a DuckDB table.
    A view is created that reads from the file, keeping it in the DAG.

    Output file: ../exports/daily_revenue.parquet
    Use case: Share analytics with external tools (Jupyter, Polars, Spark)
              without requiring DuckDB access.
*/

{{
  config(
    materialized='external',
    format='parquet',
    location='../exports/daily_revenue.parquet'
  )
}}

select
    date_key,
    day_of_week_name,
    is_weekend,
    is_holiday,
    week_of_year,
    total_trips,
    total_passengers,
    total_fare_revenue,
    total_tip_revenue,
    total_revenue,
    avg_trip_revenue,
    avg_tip_percentage,
    credit_card_trips,
    cash_trips,
    avg_trip_distance,
    avg_trip_duration_min,
    cumulative_revenue,
    revenue_change_vs_prior_day

from {{ ref('mart_daily_revenue') }}

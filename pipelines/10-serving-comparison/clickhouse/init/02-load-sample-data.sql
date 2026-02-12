-- Load sample seed data into dimension tables
-- In production, Gold layer data would come from pipeline 01's dbt output

INSERT INTO nyc_taxi.dim_payment_types VALUES
    (1, 'Credit card'), (2, 'Cash'), (3, 'No charge'),
    (4, 'Dispute'), (5, 'Unknown'), (6, 'Voided trip');

-- Note: fct_trips and mart tables would be loaded from pipeline output
-- via: clickhouse-client --query "INSERT INTO nyc_taxi.fct_trips FORMAT Parquet" < data.parquet

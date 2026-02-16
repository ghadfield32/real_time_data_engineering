-- =============================================================================
-- Pipeline 12: PostgreSQL Source Database Initialization
-- =============================================================================
-- Creates the taxi_trips table for CDC capture via Debezium.
-- WAL level is set to 'logical' via the postgres command flag in docker-compose.
-- =============================================================================

-- Create the taxi trips table matching the parquet schema
CREATE TABLE taxi_trips (
    id SERIAL PRIMARY KEY,
    "VendorID" INTEGER,
    tpep_pickup_datetime TIMESTAMP,
    tpep_dropoff_datetime TIMESTAMP,
    passenger_count DOUBLE PRECISION,
    trip_distance DOUBLE PRECISION,
    "RatecodeID" DOUBLE PRECISION,
    store_and_fwd_flag TEXT,
    "PULocationID" INTEGER,
    "DOLocationID" INTEGER,
    payment_type INTEGER,
    fare_amount DOUBLE PRECISION,
    extra DOUBLE PRECISION,
    mta_tax DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION,
    tolls_amount DOUBLE PRECISION,
    improvement_surcharge DOUBLE PRECISION,
    total_amount DOUBLE PRECISION,
    congestion_surcharge DOUBLE PRECISION,
    "Airport_fee" DOUBLE PRECISION
);

-- Create publication for Debezium logical replication
CREATE PUBLICATION taxi_publication FOR TABLE taxi_trips;

-- =============================================================================
-- Pipeline 01: Flink SQL - Kafka Source Table
-- =============================================================================
-- Creates a Flink SQL table backed by the Kafka topic taxi.raw_trips.
-- The data generator produces JSON records with these exact field names
-- matching the NYC Yellow Taxi parquet schema.
-- =============================================================================

CREATE TABLE kafka_raw_trips (
    VendorID                BIGINT,
    tpep_pickup_datetime    STRING,
    tpep_dropoff_datetime   STRING,
    passenger_count         BIGINT,
    trip_distance           DOUBLE,
    RatecodeID              BIGINT,
    store_and_fwd_flag      STRING,
    PULocationID            BIGINT,
    DOLocationID            BIGINT,
    payment_type            BIGINT,
    fare_amount             DOUBLE,
    extra                   DOUBLE,
    mta_tax                 DOUBLE,
    tip_amount              DOUBLE,
    tolls_amount            DOUBLE,
    improvement_surcharge   DOUBLE,
    total_amount            DOUBLE,
    congestion_surcharge    DOUBLE,
    Airport_fee             DOUBLE
) WITH (
    'connector' = 'kafka',
    'topic' = 'taxi.raw_trips',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-consumer',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'json'
);

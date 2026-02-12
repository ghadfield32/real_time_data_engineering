-- Pipeline 06: Create Kafka source in RisingWave (via Redpanda broker)
-- This source continuously ingests JSON events from the taxi.raw_trips topic.

CREATE SOURCE IF NOT EXISTS taxi_raw_source (
    "VendorID" BIGINT,
    tpep_pickup_datetime VARCHAR,
    tpep_dropoff_datetime VARCHAR,
    passenger_count BIGINT,
    trip_distance DOUBLE PRECISION,
    "RatecodeID" BIGINT,
    store_and_fwd_flag VARCHAR,
    "PULocationID" BIGINT,
    "DOLocationID" BIGINT,
    payment_type BIGINT,
    fare_amount DOUBLE PRECISION,
    extra DOUBLE PRECISION,
    mta_tax DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION,
    tolls_amount DOUBLE PRECISION,
    improvement_surcharge DOUBLE PRECISION,
    total_amount DOUBLE PRECISION,
    congestion_surcharge DOUBLE PRECISION,
    "Airport_fee" DOUBLE PRECISION
) WITH (
    connector = 'kafka',
    topic = 'taxi.raw_trips',
    properties.bootstrap.server = 'redpanda:9092',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;

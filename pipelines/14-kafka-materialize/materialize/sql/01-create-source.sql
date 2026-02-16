-- Pipeline 14: Create Kafka connection and source in Materialize
-- Materialize requires an explicit CONNECTION object before creating a SOURCE.

-- Create connection to the Kafka broker
CREATE CONNECTION IF NOT EXISTS kafka_conn TO KAFKA (BROKER 'kafka:9092');

-- Create source from Kafka topic
-- Materialize ingests each Kafka message as raw TEXT; we parse JSON downstream.
CREATE SOURCE IF NOT EXISTS taxi_source
FROM KAFKA CONNECTION kafka_conn (TOPIC 'taxi.raw_trips')
FORMAT TEXT
ENVELOPE NONE;

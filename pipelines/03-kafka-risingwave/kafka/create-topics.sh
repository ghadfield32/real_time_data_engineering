#!/bin/bash
# Pipeline 03 - Create Kafka topics for RisingWave pipeline
set -e

BROKER="${KAFKA_BROKER:-localhost:9092}"

echo "Creating Kafka topics on ${BROKER}..."

# Wait for Kafka to be ready
until /opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BROKER}" --list 2>/dev/null; do
    echo "  Waiting for Kafka to be ready..."
    sleep 3
done

# Create the taxi raw trips topic
/opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${BROKER}" \
    --create --if-not-exists \
    --topic taxi.raw_trips \
    --partitions 3 \
    --replication-factor 1

echo "Topic 'taxi.raw_trips' created successfully."

# List all topics
echo ""
echo "Current topics:"
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BROKER}" --list

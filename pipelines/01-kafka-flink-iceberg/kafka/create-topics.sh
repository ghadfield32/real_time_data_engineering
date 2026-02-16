#!/bin/bash
# =============================================================================
# Pipeline 01: Create Kafka Topics
# =============================================================================
# Creates the required topics for the taxi trip streaming pipeline.
# Run this after Kafka is fully started and healthy.
#
# Usage:
#   docker compose exec kafka /bin/bash /opt/kafka/scripts/create-topics.sh
#   -- or --
#   make create-topics
# =============================================================================

set -euo pipefail

BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-localhost:9092}"
KAFKA_BIN="/opt/kafka/bin"

echo "============================================================"
echo "  Creating Kafka Topics"
echo "  Bootstrap server: ${BOOTSTRAP_SERVER}"
echo "============================================================"

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
MAX_RETRIES=30
RETRY=0
until ${KAFKA_BIN}/kafka-broker-api-versions.sh --bootstrap-server "${BOOTSTRAP_SERVER}" > /dev/null 2>&1; do
    RETRY=$((RETRY + 1))
    if [ "${RETRY}" -ge "${MAX_RETRIES}" ]; then
        echo "ERROR: Kafka not available after ${MAX_RETRIES} retries"
        exit 1
    fi
    echo "  Attempt ${RETRY}/${MAX_RETRIES} - waiting..."
    sleep 2
done
echo "Kafka is ready."
echo ""

# ---------------------------------------------------------------------------
# taxi.raw_trips - Main ingest topic
# ---------------------------------------------------------------------------
echo "Creating topic: taxi.raw_trips"
${KAFKA_BIN}/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --create \
    --topic taxi.raw_trips \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists \
    --config retention.ms=86400000 \
    --config cleanup.policy=delete \
    --config segment.bytes=104857600

echo "  taxi.raw_trips created (3 partitions, 24h retention)"
echo ""

# ---------------------------------------------------------------------------
# taxi.raw_trips.dlq - Dead Letter Queue for failed/invalid events
# ---------------------------------------------------------------------------
echo "Creating topic: taxi.raw_trips.dlq"
${KAFKA_BIN}/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --create \
    --topic taxi.raw_trips.dlq \
    --partitions 1 \
    --replication-factor 1 \
    --if-not-exists \
    --config retention.ms=604800000 \
    --config cleanup.policy=delete

echo "  taxi.raw_trips.dlq created (1 partition, 7d retention)"
echo ""

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
echo "============================================================"
echo "  Topics:"
${KAFKA_BIN}/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --list

echo ""
echo "  Topic Details:"
${KAFKA_BIN}/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --describe \
    --topic taxi.raw_trips

echo "============================================================"
echo "  Topic creation complete."
echo "============================================================"

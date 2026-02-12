#!/usr/bin/env bash
###############################################################################
# Create Kafka topics for Pipeline 02 (Kafka + Spark + Iceberg)
#
# Usage:
#   docker compose exec kafka /bin/bash /opt/kafka/scripts/create-topics.sh
#   OR called via: make topics
###############################################################################

set -euo pipefail

BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-localhost:9092}"

echo "============================================="
echo "  Creating Kafka topics"
echo "  Bootstrap: ${BOOTSTRAP_SERVER}"
echo "============================================="

# Wait for Kafka to be ready
MAX_WAIT=60
WAITED=0
until /opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP_SERVER}" --list >/dev/null 2>&1; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "ERROR: Kafka not ready after ${MAX_WAIT}s"
        exit 1
    fi
    echo "  Waiting for Kafka... (${WAITED}s)"
    sleep 5
    WAITED=$((WAITED + 5))
done

echo "  Kafka is ready."

# Create topics
/opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --create --if-not-exists \
    --topic taxi.raw_trips \
    --partitions 6 \
    --replication-factor 1

echo ""
echo "  Topics created successfully:"
/opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --list

echo "============================================="

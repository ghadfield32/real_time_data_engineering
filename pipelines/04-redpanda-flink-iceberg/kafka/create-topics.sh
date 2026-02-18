#!/bin/bash
# =============================================================================
# Pipeline 04: Create Redpanda Topics
# =============================================================================
# Creates the required topics for the taxi trip streaming pipeline.
# Uses rpk (Redpanda CLI) instead of kafka-topics.sh.
#
# Usage:
#   docker compose exec redpanda rpk topic create ...
#   -- or --
#   make create-topics
# =============================================================================

set -euo pipefail

echo "Creating topics via rpk..."
rpk topic create taxi.raw_trips \
    --brokers redpanda:9092 \
    --partitions 3 \
    --replicas 1 \
    --topic-config retention.ms=259200000 \
    --topic-config cleanup.policy=delete || true

# Dead Letter Queue: for poison messages that fail processing
rpk topic create taxi.raw_trips.dlq \
    --brokers redpanda:9092 \
    --partitions 1 \
    --replicas 1 \
    --topic-config retention.ms=604800000 \
    --topic-config cleanup.policy=delete || true

rpk topic list --brokers redpanda:9092
echo "Topic creation complete."

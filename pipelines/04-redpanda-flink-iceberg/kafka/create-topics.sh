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
rpk topic create taxi.raw_trips --brokers redpanda:9092 --partitions 3 --replicas 1 || true
rpk topic list --brokers redpanda:9092
echo "Topic creation complete."

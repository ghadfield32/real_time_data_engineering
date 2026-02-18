#!/bin/bash
# =============================================================================
# Template Pipeline: Create Redpanda Topics
# =============================================================================
# Run via Makefile: make create-topics
# Or directly: docker compose exec redpanda rpk topic create ...
#
# TODO: Replace DOMAIN with your domain name (e.g., stock_ticks, orders, iot)
# =============================================================================

set -euo pipefail

echo "Creating topics via rpk..."

# Primary topic: 3 partitions allows Flink to parallelize reads across 3 tasks.
# Retention 3 days (259200000ms) — adjust based on your event volume and SLA.
# TODO: Replace DOMAIN.raw_events with your topic name
rpk topic create DOMAIN.raw_events \
    --brokers redpanda:9092 \
    --partitions 3 \
    --replicas 1 \
    --topic-config retention.ms=259200000 \
    --topic-config cleanup.policy=delete || true

# Dead Letter Queue (DLQ): 1 partition, 7-day retention.
# Events land here when the processing pipeline detects a poison message.
# Monitor this topic — messages here indicate data quality or schema issues.
# TODO: Replace DOMAIN.raw_events.dlq with your DLQ topic name
rpk topic create DOMAIN.raw_events.dlq \
    --brokers redpanda:9092 \
    --partitions 1 \
    --replicas 1 \
    --topic-config retention.ms=604800000 \
    --topic-config cleanup.policy=delete || true

rpk topic list --brokers redpanda:9092
echo "Topic creation complete."

#!/bin/bash
set -euo pipefail
echo "Creating topics via rpk..."
rpk topic create taxi.raw_trips --brokers redpanda:9092 --partitions 6 --replicas 1 || true
rpk topic list --brokers redpanda:9092
echo "Topic creation complete."

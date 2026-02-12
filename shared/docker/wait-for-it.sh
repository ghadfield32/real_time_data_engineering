#!/bin/bash
# wait-for-it.sh - Wait for a service to become available
# Usage: wait-for-it.sh host:port [-t timeout] [-- command]

set -e

TIMEOUT=60
HOST=""
PORT=""
CMD=""

usage() {
    echo "Usage: $0 host:port [-t timeout] [-- command]"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        *:*)
            HOST="${1%%:*}"
            PORT="${1##*:}"
            shift
            ;;
        -t)
            TIMEOUT="$2"
            shift 2
            ;;
        --)
            shift
            CMD="$@"
            break
            ;;
        *)
            usage
            ;;
    esac
done

if [ -z "$HOST" ] || [ -z "$PORT" ]; then
    usage
fi

echo "Waiting for $HOST:$PORT (timeout: ${TIMEOUT}s)..."

start_time=$(date +%s)
while true; do
    if nc -z "$HOST" "$PORT" 2>/dev/null; then
        echo "$HOST:$PORT is available"
        break
    fi

    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    if [ "$elapsed" -ge "$TIMEOUT" ]; then
        echo "Timeout waiting for $HOST:$PORT after ${TIMEOUT}s"
        exit 1
    fi

    sleep 1
done

if [ -n "$CMD" ]; then
    exec $CMD
fi

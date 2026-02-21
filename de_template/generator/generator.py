"""Taxi trip event generator.

Reads NYC Yellow Taxi parquet data and produces events to a Kafka-compatible
broker (Kafka or Redpanda). Supports three modes:
  - burst:    As fast as possible (benchmarking)
  - realtime: Simulates actual event-time spacing
  - batch:    Sends events in configurable batch sizes with delays

Configuration via environment variables:
  BROKER_URL    Kafka/Redpanda bootstrap servers  (default: localhost:9092)
  TOPIC         Target topic name                  (default: taxi.raw_trips)
  MODE          burst | realtime | batch           (default: burst)
  RATE_LIMIT    Max events/sec in burst mode, 0=unlimited (default: 0)
  BATCH_SIZE    Events per batch in batch mode     (default: 1000)
  BATCH_DELAY   Seconds between batches            (default: 1.0)
  DATA_PATH     Path to parquet file               (default: /data/yellow_tripdata_2024-01.parquet)
  MAX_EVENTS    Stop after N events, 0=all         (default: 0)
  METRICS_PATH  Write JSON metrics to this path    (default: /tmp/generator_metrics.json)

Usage:
    python generator.py
    python generator.py --mode burst --broker localhost:9092
"""

import argparse
import math
import os
import sys
import time
from datetime import datetime

import orjson
import pyarrow.parquet as pq
from confluent_kafka import Producer


def delivery_callback(err, msg):
    if err is not None:
        print(f"  [ERROR] Delivery failed: {err}", file=sys.stderr)


def read_parquet(path: str, max_events: int = 0):
    """Yield rows from parquet file as dicts."""
    table = pq.read_table(path)
    total = table.num_rows if max_events == 0 else min(max_events, table.num_rows)
    print(f"  Source: {path} ({table.num_rows:,} rows, sending {total:,})")

    batches = table.to_batches(max_chunksize=10_000)
    sent = 0
    for batch in batches:
        for row in batch.to_pylist():
            if sent >= total:
                return
            # Convert timestamps to ISO strings for JSON serialization
            for key, val in row.items():
                if isinstance(val, datetime):
                    row[key] = val.isoformat()
            yield row
            sent += 1


def create_producer(broker_url: str) -> Producer:
    conf = {
        "bootstrap.servers": broker_url,
        "enable.idempotence": True,
        "acks": "all",
        "linger.ms": 5,
        "batch.num.messages": 10000,
        "queue.buffering.max.messages": 500000,
        "queue.buffering.max.kbytes": 1048576,
        "compression.type": "lz4",
    }
    return Producer(conf)


def produce_burst(producer: Producer, topic: str, rows, rate_limit: int):
    """Produce as fast as possible, optionally rate-limited."""
    count = 0
    start = time.perf_counter()
    last_report = start

    for row in rows:
        key = str(row.get("PULocationID", "")).encode("utf-8")
        value = orjson.dumps(row)
        producer.produce(topic, value=value, key=key, callback=delivery_callback)
        count += 1

        if count % 10000 == 0:
            producer.poll(0)
            now = time.perf_counter()
            if now - last_report >= 5.0:
                elapsed = now - start
                rate = count / elapsed
                print(f"  Produced {count:,} events ({rate:,.0f} evt/s)")
                last_report = now

        # Rate limiting
        if rate_limit > 0 and count % rate_limit == 0:
            elapsed = time.perf_counter() - start
            expected = count / rate_limit
            if elapsed < expected:
                time.sleep(expected - elapsed)

    producer.flush(timeout=30)
    elapsed = time.perf_counter() - start
    rate = count / elapsed if elapsed > 0 else 0
    return count, elapsed, rate


def produce_batch(producer: Producer, topic: str, rows, batch_size: int, batch_delay: float):
    """Produce in fixed-size batches with delays between them."""
    count = 0
    batch_count = 0
    start = time.perf_counter()

    batch_buffer = []
    for row in rows:
        batch_buffer.append(row)
        if len(batch_buffer) >= batch_size:
            for r in batch_buffer:
                key = str(r.get("PULocationID", "")).encode("utf-8")
                value = orjson.dumps(r)
                producer.produce(topic, value=value, key=key, callback=delivery_callback)
                count += 1
            producer.flush(timeout=30)
            batch_count += 1
            elapsed = time.perf_counter() - start
            rate = count / elapsed if elapsed > 0 else 0
            print(f"  Batch {batch_count}: {count:,} total ({rate:,.0f} evt/s)")
            batch_buffer = []
            time.sleep(batch_delay)

    # Final partial batch
    if batch_buffer:
        for r in batch_buffer:
            key = str(r.get("PULocationID", "")).encode("utf-8")
            value = orjson.dumps(r)
            producer.produce(topic, value=value, key=key, callback=delivery_callback)
            count += 1
        producer.flush(timeout=30)

    elapsed = time.perf_counter() - start
    rate = count / elapsed if elapsed > 0 else 0
    return count, elapsed, rate


def main():
    parser = argparse.ArgumentParser(description="Taxi trip event generator")
    parser.add_argument("--broker", default=os.environ.get("BROKER_URL", "localhost:9092"))
    parser.add_argument("--topic", default=os.environ.get("TOPIC", "taxi.raw_trips"))
    parser.add_argument("--mode", default=os.environ.get("MODE", "burst"),
                        choices=["burst", "realtime", "batch"])
    parser.add_argument("--rate-limit", type=int,
                        default=int(os.environ.get("RATE_LIMIT", "0")))
    parser.add_argument("--batch-size", type=int,
                        default=int(os.environ.get("BATCH_SIZE", "1000")))
    parser.add_argument("--batch-delay", type=float,
                        default=float(os.environ.get("BATCH_DELAY", "1.0")))
    parser.add_argument("--data-path",
                        default=os.environ.get("DATA_PATH", "/data/yellow_tripdata_2024-01.parquet"))
    parser.add_argument("--max-events", type=int,
                        default=int(os.environ.get("MAX_EVENTS", "0")))
    args = parser.parse_args()

    print("=" * 60)
    print("  Taxi Trip Event Generator")
    print("=" * 60)
    print(f"  Broker:     {args.broker}")
    print(f"  Topic:      {args.topic}")
    print(f"  Mode:       {args.mode}")
    print(f"  Data:       {args.data_path}")
    max_events_str = "all" if args.max_events == 0 else f"{args.max_events:,}"
    print(f"  Max events: {max_events_str}")
    print()

    producer = create_producer(args.broker)
    rows = read_parquet(args.data_path, args.max_events)

    if args.mode == "burst":
        count, elapsed, rate = produce_burst(producer, args.topic, rows, args.rate_limit)
    elif args.mode == "batch":
        count, elapsed, rate = produce_batch(
            producer, args.topic, rows, args.batch_size, args.batch_delay
        )
    else:
        # realtime mode: use burst with rate limiting to approximate real-time
        count, elapsed, rate = produce_burst(producer, args.topic, rows, rate_limit=5000)

    print()
    print("=" * 60)
    print("  GENERATOR COMPLETE")
    print(f"  Events:  {count:,}")
    print(f"  Elapsed: {elapsed:.2f}s")
    print(f"  Rate:    {rate:,.0f} events/sec")
    print("=" * 60)

    # Write metrics for validate.sh data-derived count checks
    metrics_path = os.environ.get("METRICS_PATH", "/tmp/generator_metrics.json")
    metrics = {
        "events": count,
        "elapsed_seconds": round(elapsed, 3),
        "events_per_second": round(rate, 1),
        "mode": args.mode,
        "broker": args.broker,
        "topic": args.topic,
    }
    with open(metrics_path, "wb") as f:
        f.write(orjson.dumps(metrics))
    print(f"  Metrics written to {metrics_path}")


if __name__ == "__main__":
    main()

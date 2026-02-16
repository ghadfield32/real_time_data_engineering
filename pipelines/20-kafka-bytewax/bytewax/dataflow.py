"""
Bytewax Dataflow: NYC Taxi Trip Stream Processing

Reads from Kafka topic taxi.raw_trips, processes through
Bronze (rename/cast) and Silver (quality filter + enrich) stages,
writes results to taxi.bronze and taxi.silver Kafka topics.
"""
import json
import hashlib
import os
from datetime import datetime, timedelta

from bytewax.dataflow import Dataflow
from bytewax import operators as op
from bytewax.connectors.kafka import KafkaSource, KafkaSink

KAFKA_BROKERS = [os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")]
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "taxi.raw_trips")
BRONZE_TOPIC = os.getenv("BRONZE_TOPIC", "taxi.bronze")
SILVER_TOPIC = os.getenv("SILVER_TOPIC", "taxi.silver")

flow = Dataflow("taxi-processor")

# Source: Read from Kafka
kafka_source = KafkaSource(
    brokers=KAFKA_BROKERS,
    topics=[INPUT_TOPIC],
    starting_offset=-2,  # -2 = beginning, -1 = end (Kafka offset semantics)
    batch_size=100,
)
raw_stream = op.input("kafka-input", flow, kafka_source)


def parse_raw(msg):
    """Parse raw Kafka message to dict."""
    try:
        value = msg.value.decode("utf-8") if isinstance(msg.value, bytes) else msg.value
        return json.loads(value)
    except Exception:
        return None


parsed = op.map("parse", raw_stream, parse_raw)
valid = op.filter("filter-none", parsed, lambda x: x is not None)


def to_bronze(raw):
    """Bronze: Rename columns, cast types."""
    return {
        "vendor_id": int(raw.get("VendorID", 0) or 0),
        "pickup_datetime": raw.get("tpep_pickup_datetime", ""),
        "dropoff_datetime": raw.get("tpep_dropoff_datetime", ""),
        "passenger_count": float(raw.get("passenger_count", 0) or 0),
        "trip_distance": float(raw.get("trip_distance", 0) or 0),
        "rate_code_id": int(raw.get("RatecodeID", 0) or 0),
        "store_and_fwd_flag": raw.get("store_and_fwd_flag", ""),
        "pickup_location_id": int(raw.get("PULocationID", 0) or 0),
        "dropoff_location_id": int(raw.get("DOLocationID", 0) or 0),
        "payment_type": int(raw.get("payment_type", 0) or 0),
        "fare_amount": round(float(raw.get("fare_amount", 0) or 0), 2),
        "extra": round(float(raw.get("extra", 0) or 0), 2),
        "mta_tax": round(float(raw.get("mta_tax", 0) or 0), 2),
        "tip_amount": round(float(raw.get("tip_amount", 0) or 0), 2),
        "tolls_amount": round(float(raw.get("tolls_amount", 0) or 0), 2),
        "improvement_surcharge": round(float(raw.get("improvement_surcharge", 0) or 0), 2),
        "total_amount": round(float(raw.get("total_amount", 0) or 0), 2),
        "congestion_surcharge": round(float(raw.get("congestion_surcharge", 0) or 0), 2),
        "airport_fee": round(float(raw.get("Airport_fee", 0) or 0), 2),
    }


bronze = op.map("bronze", valid, to_bronze)

# Serialize to JSON string (KafkaSink will encode)
def serialize_to_json(record):
    """Serialize dict to JSON string."""
    return json.dumps(record)

bronze_serialized = op.map("bronze-serialize", bronze, serialize_to_json)

# Write bronze to Kafka
bronze_sink = KafkaSink(
    brokers=KAFKA_BROKERS,
    topic=BRONZE_TOPIC,
)

op.output("bronze-output", bronze_serialized, bronze_sink)


def to_silver(b):
    """Silver: Quality filters + enrichment."""
    if not b.get("pickup_datetime") or not b.get("dropoff_datetime"):
        return None
    if b.get("trip_distance", 0) < 0 or b.get("fare_amount", 0) < 0:
        return None

    # Generate trip_id
    key = "|".join([
        str(b["vendor_id"]),
        str(b["pickup_datetime"]),
        str(b["dropoff_datetime"]),
        str(b["pickup_location_id"]),
        str(b["dropoff_location_id"]),
        str(b["fare_amount"]),
        str(b["total_amount"]),
    ])
    b["trip_id"] = hashlib.md5(key.encode()).hexdigest()

    # Compute duration
    try:
        pickup = datetime.fromisoformat(b["pickup_datetime"])
        dropoff = datetime.fromisoformat(b["dropoff_datetime"])
        b["trip_duration_minutes"] = round((dropoff - pickup).total_seconds() / 60, 2)
    except Exception:
        b["trip_duration_minutes"] = 0

    return b


silver = op.map("silver", bronze, to_silver)
silver_valid = op.filter("silver-filter", silver, lambda x: x is not None)

# Serialize to JSON string (KafkaSink will encode)
silver_serialized = op.map("silver-serialize", silver_valid, lambda r: json.dumps(r))

silver_sink = KafkaSink(
    brokers=KAFKA_BROKERS,
    topic=SILVER_TOPIC,
)

op.output("silver-output", silver_serialized, silver_sink)

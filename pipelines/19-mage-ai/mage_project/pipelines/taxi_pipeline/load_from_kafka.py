"""
Data Loader: Read taxi events from Kafka topic
"""
import json
import os

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader

@data_loader
def load_from_kafka(*args, **kwargs):
    """Load taxi trip events from Kafka topic."""
    from kafka import KafkaConsumer

    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    topic = 'taxi.raw_trips'

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset='earliest',
        consumer_timeout_ms=10000,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        group_id='mage-taxi-consumer',
    )

    records = []
    for message in consumer:
        records.append(message.value)

    consumer.close()
    print(f"Loaded {len(records)} records from Kafka")
    return records

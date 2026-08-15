"""
Akaal — Streaming & Event Platform Adapters (P4.5)
=================================================
Canonical adapters for Apache Kafka, Confluent Platform, Amazon MSK,
Amazon Kinesis, Azure Event Hubs, and Google Cloud Pub/Sub.
"""

from akaal.adapters.streaming.kafka_adapter import KafkaAdapter, ConfluentAdapter, MSKAdapter
from akaal.adapters.streaming.kinesis_adapter import KinesisAdapter
from akaal.adapters.streaming.eventhubs_adapter import EventHubsAdapter
from akaal.adapters.streaming.pubsub_adapter import PubSubAdapter

__all__ = [
    "KafkaAdapter",
    "ConfluentAdapter",
    "MSKAdapter",
    "KinesisAdapter",
    "EventHubsAdapter",
    "PubSubAdapter",
]

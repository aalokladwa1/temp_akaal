"""
akaalEngine.connection.providers.streaming
==========================================
Message queue and event stream provider strategies.
"""

from akaalEngine.connection.providers.streaming.kafka import KafkaProviderStrategy
from akaalEngine.connection.providers.streaming.kinesis import KinesisProviderStrategy
from akaalEngine.connection.providers.streaming.eventhubs import EventHubsProviderStrategy
from akaalEngine.connection.providers.streaming.pubsub import PubSubProviderStrategy

__all__ = [
    "KafkaProviderStrategy",
    "KinesisProviderStrategy",
    "EventHubsProviderStrategy",
    "PubSubProviderStrategy",
]

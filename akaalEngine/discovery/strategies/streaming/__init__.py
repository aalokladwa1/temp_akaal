"""
akaalEngine.discovery.strategies.streaming
==========================================
Streaming event bus discovery strategies.
"""

from akaalEngine.discovery.strategies.streaming.eventhubs import EventHubsDiscoveryStrategy
from akaalEngine.discovery.strategies.streaming.kafka import KafkaDiscoveryStrategy
from akaalEngine.discovery.strategies.streaming.kinesis import KinesisDiscoveryStrategy
from akaalEngine.discovery.strategies.streaming.pubsub import PubSubDiscoveryStrategy
from akaalEngine.discovery.strategies.streaming.rabbitmq import RabbitMQDiscoveryStrategy
from akaalEngine.discovery.strategies.streaming.pulsar import PulsarDiscoveryStrategy

__all__ = [
    "KafkaDiscoveryStrategy",
    "KinesisDiscoveryStrategy",
    "EventHubsDiscoveryStrategy",
    "PubSubDiscoveryStrategy",
    "RabbitMQDiscoveryStrategy",
    "PulsarDiscoveryStrategy",
]

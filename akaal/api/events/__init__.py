"""
Events package initialization.
"""

from akaal.api.events.models import (
    DomainEvent,
    MigrationStarted,
    MigrationCompleted,
    MigrationFailed,
    SchemaChanged,
    ValidationFinished,
    JobCancelled,
)
from akaal.api.events.publisher import IEventPublisher
from akaal.api.events.memory import InMemoryEventPublisher
from akaal.api.events.kafka import KafkaEventPublisher
from akaal.api.events.rabbitmq import RabbitMQEventPublisher
from akaal.api.events.outbox import TransactionalOutbox, OutboxRecord

__all__ = [
    "DomainEvent",
    "MigrationStarted",
    "MigrationCompleted",
    "MigrationFailed",
    "SchemaChanged",
    "ValidationFinished",
    "JobCancelled",
    "IEventPublisher",
    "InMemoryEventPublisher",
    "KafkaEventPublisher",
    "RabbitMQEventPublisher",
    "TransactionalOutbox",
    "OutboxRecord",
]

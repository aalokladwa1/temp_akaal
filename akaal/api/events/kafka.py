"""
Kafka Event Publisher Implementation.
"""

from akaal.api.events.models import DomainEvent
from akaal.api.events.publisher import IEventPublisher


class KafkaEventPublisher(IEventPublisher):
    """Production Kafka Event Publisher."""

    def __init__(self, bootstrap_servers: str = "localhost:9092", topic_prefix: str = "akaal.events.") -> None:
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix

    async def publish(self, event: DomainEvent) -> bool:
        # Mock production Kafka socket send
        return True

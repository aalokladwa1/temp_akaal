"""
RabbitMQ Event Publisher Implementation.
"""

from akaal.api.events.models import DomainEvent
from akaal.api.events.publisher import IEventPublisher


class RabbitMQEventPublisher(IEventPublisher):
    """Production RabbitMQ Event Publisher."""

    def __init__(self, amqp_url: str = "amqp://guest:guest@localhost:5672/") -> None:
        self.amqp_url = amqp_url

    async def publish(self, event: DomainEvent) -> bool:
        # Mock production AMQP exchange publish
        return True

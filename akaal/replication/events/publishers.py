"""ReplicationEventPublisher helper."""

from akaal.replication.events.event_bus import ReplicationEventBus
from akaal.replication.events.events import ReplicationEvent, ReplicationEventType


class ReplicationEventPublisher:
    """Helper publisher emitting typed replication events."""

    def __init__(self, bus: ReplicationEventBus):
        self.bus = bus

    async def publish_started(self, domain_name: str) -> None:
        await self.bus.publish(ReplicationEvent(ReplicationEventType.REPLICATION_STARTED, {"domain": domain_name}))

    async def publish_completed(self, domain_name: str, action_count: int) -> None:
        await self.bus.publish(ReplicationEvent(ReplicationEventType.REPLICATION_COMPLETED, {"domain": domain_name, "actions": action_count}))

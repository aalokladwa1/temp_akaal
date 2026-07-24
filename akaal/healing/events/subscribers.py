"""HealingEventSubscriber & HealingMetricsSubscriber."""

from typing import Dict
from akaal.healing.events.events import HealingEvent


class HealingEventSubscriber:
    """Base subscriber."""
    pass


class HealingMetricsSubscriber:
    """Subscribes and tracks metrics for healing events."""

    def __init__(self):
        self.event_counts: Dict[str, int] = {}

    async def on_event(self, event: HealingEvent) -> None:
        key = event.event_type.value
        self.event_counts[key] = self.event_counts.get(key, 0) + 1

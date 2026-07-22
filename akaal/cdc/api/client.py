"""
CDCClient Public Client Facade for Platform 4.
"""

from typing import List, Optional
from akaal.cdc.contracts.dto import CDCSessionDTO, FailoverStatusDTO, ReplayResultDTO
from akaal.cdc.contracts.event import CDCEvent
from akaal.cdc.coordinator.coordinator import CDCCoordinator


class CDCClient:
    """Public Client Facade providing simple API access to Platform 4 CDC."""

    def __init__(self, coordinator: Optional[CDCCoordinator] = None) -> None:
        self.coordinator = coordinator or CDCCoordinator()

    async def start_cdc_session(self, source_engine: str, source_db: str, target_dbs: List[str]) -> CDCSessionDTO:
        """Start a multi-source, multi-target CDC session."""
        return await self.coordinator.start_session(source_engine, source_db, target_dbs)

    async def process_cdc_event(self, event: CDCEvent) -> bool:
        """Process and route a captured CDC event."""
        return await self.coordinator.process_cdc_event(event)

    async def replay_cdc_events(self, events: List[CDCEvent], start_pos: str, end_pos: str) -> ReplayResultDTO:
        """Replay historical CDC events with exactly-once deduplication."""
        return await self.coordinator.replay(events, start_pos, end_pos)

    async def trigger_live_failover(self, failed_node: str, new_node: str) -> FailoverStatusDTO:
        """Trigger live failover recovery."""
        return await self.coordinator.failover(failed_node, new_node)

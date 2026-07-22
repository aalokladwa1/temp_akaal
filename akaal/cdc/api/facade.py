"""
IPlatform4Facade Interface and Platform4Facade Implementation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from akaal.cdc.api.client import CDCClient
from akaal.cdc.contracts.dto import CDCSessionDTO, FailoverStatusDTO, ReplayResultDTO
from akaal.cdc.contracts.event import CDCEvent


class IPlatform4Facade(ABC):
    """Abstract Interface for Platform 4 Enterprise CDC Façade."""

    @abstractmethod
    async def start_cdc_session(self, source_engine: str, source_db: str, target_dbs: List[str]) -> CDCSessionDTO:
        pass

    @abstractmethod
    async def process_event(self, event: CDCEvent) -> bool:
        pass

    @abstractmethod
    async def replay_events(self, events: List[CDCEvent], start_pos: str, end_pos: str) -> ReplayResultDTO:
        pass

    @abstractmethod
    async def failover_sync(self, failed_node: str, new_node: str) -> FailoverStatusDTO:
        pass


class Platform4Facade(IPlatform4Facade):
    """Production Implementation of Platform 4 Façade."""

    def __init__(self, client: Optional[CDCClient] = None) -> None:
        self.client = client or CDCClient()

    async def start_cdc_session(self, source_engine: str, source_db: str, target_dbs: List[str]) -> CDCSessionDTO:
        return await self.client.start_cdc_session(source_engine, source_db, target_dbs)

    async def process_event(self, event: CDCEvent) -> bool:
        return await self.client.process_cdc_event(event)

    async def replay_events(self, events: List[CDCEvent], start_pos: str, end_pos: str) -> ReplayResultDTO:
        return await self.client.replay_cdc_events(events, start_pos, end_pos)

    async def failover_sync(self, failed_node: str, new_node: str) -> FailoverStatusDTO:
        return await self.client.trigger_live_failover(failed_node, new_node)

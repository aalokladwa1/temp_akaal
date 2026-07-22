"""
Platform 4 Public Façade — CDC & Replay Integration.
"""

from typing import Optional
from akaal.api.contracts.dto import CapabilityDTO
from akaal.api.facades.base import IFacade
from akaal.cdc.api.facade import Platform4Facade as ConcretePlatform4Facade, IPlatform4Facade


class Platform4Facade(IFacade, IPlatform4Facade):
    """Platform 7 Integration Wrapper for Platform 4 CDC."""

    def __init__(self, inner_facade: Optional[IPlatform4Facade] = None) -> None:
        self._inner = inner_facade or ConcretePlatform4Facade()

    async def get_capabilities(self) -> CapabilityDTO:
        return CapabilityDTO(
            platform_name="Platform 4 (CDC & Replay)",
            version="1.0.0",
            supported_features=[
                "distributed_cdc",
                "remote_cdc",
                "multi_source_cdc",
                "multi_target_cdc",
                "cdc_routing",
                "cdc_replay",
                "cdc_buffering",
                "checkpoint_sync",
                "failover_sync",
            ],
            active_protocols=["Events", "gRPC", "REST"],
        )

    async def start_cdc_session(self, source_engine: str, source_db: str, target_dbs: list) -> dict:
        return await self._inner.start_cdc_session(source_engine, source_db, target_dbs)

    async def process_event(self, event) -> bool:
        return await self._inner.process_event(event)

    async def replay_events(self, events: list, start_pos: str, end_pos: str) -> dict:
        return await self._inner.replay_events(events, start_pos, end_pos)

    async def failover_sync(self, failed_node: str, new_node: str) -> dict:
        return await self._inner.failover_sync(failed_node, new_node)

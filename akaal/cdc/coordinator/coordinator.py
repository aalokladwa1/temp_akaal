"""
Overall CDC Coordinator Engine.
"""

from typing import Dict, List, Optional
import datetime
import uuid

from akaal.cdc.buffering.buffer import DurableCDCBuffer
from akaal.cdc.checkpoint.base import ICheckpointStore
from akaal.cdc.checkpoint.memory import MemoryCheckpointStore
from akaal.cdc.contracts.checkpoint import Checkpoint, Position
from akaal.cdc.contracts.dto import CDCSessionDTO, FailoverStatusDTO, ReplayResultDTO
from akaal.cdc.contracts.event import CDCEvent
from akaal.cdc.failover.coordinator import CDCFailoverCoordinator
from akaal.cdc.replay.engine import CDCReplayEngine
from akaal.cdc.routing.engine import CDCRoutingEngine
from akaal.cdc.sources.base import ICDCSourceAdapter
from akaal.cdc.sources.postgres import PostgresWALAdapter
from akaal.cdc.targets.generic import GenericDatabaseTargetAdapter
from akaal.cdc.transport.base import ICDCTransport
from akaal.cdc.transport.memory import InMemoryCDCTransport


class CDCCoordinator:
    """Master CDC Coordinator orchestrating all Platform 4 CDC capabilities."""

    def __init__(
        self,
        transport: Optional[ICDCTransport] = None,
        checkpoint_store: Optional[ICheckpointStore] = None,
    ) -> None:
        self.transport = transport or InMemoryCDCTransport()
        self.checkpoint_store = checkpoint_store or MemoryCheckpointStore()
        self.router = CDCRoutingEngine()
        self.buffer = DurableCDCBuffer()
        self.replay_engine = CDCReplayEngine()
        self.failover_coordinator = CDCFailoverCoordinator()
        self.target_adapter = GenericDatabaseTargetAdapter()

        self._active_sessions: Dict[str, CDCSessionDTO] = {}
        self._sources: Dict[str, ICDCSourceAdapter] = {"POSTGRES": PostgresWALAdapter()}

    async def start_session(self, source_engine: str, source_db: str, target_dbs: List[str]) -> CDCSessionDTO:
        session_id = f"cdc-sess-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        session = CDCSessionDTO(
            session_id=session_id,
            source_engine=source_engine,
            source_db=source_db,
            target_dbs=target_dbs,
            status="RUNNING",
            captured_events_count=0,
            start_time=now,
        )
        self._active_sessions[session_id] = session
        return session

    async def process_cdc_event(self, event: CDCEvent) -> bool:
        """Process a captured CDC event through routing, buffer, transport, and target."""
        # 1. Route event
        destinations = self.router.route_event(event)

        # 2. Buffer event
        self.buffer.push_event(event)

        # 3. Transport publish
        for dest in destinations:
            await self.transport.publish_event(event, topic=dest)

        # 4. Target apply
        await self.target_adapter.apply_changes([event])

        # 5. Checkpoint save
        pos = Position(engine=event.source_engine, stream_position=event.position_lsn or "0/0")
        chk = Checkpoint(checkpoint_id=f"chk-{event.event_id}", stream_id=f"{event.source_db}.{event.source_table}", source_db=event.source_db, position=pos)
        await self.checkpoint_store.save_checkpoint(chk)

        return True

    async def get_session(self, session_id: str) -> Optional[CDCSessionDTO]:
        return self._active_sessions.get(session_id)

    async def replay(self, events: List[CDCEvent], start_pos: str, end_pos: str) -> ReplayResultDTO:
        return await self.replay_engine.replay_events(events, start_pos, end_pos)

    async def failover(self, failed_node: str, new_node: str) -> FailoverStatusDTO:
        return await self.failover_coordinator.trigger_failover(failed_node, new_node)

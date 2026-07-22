"""
PostgreSQL WAL Change Data Capture Adapter.
"""

from typing import AsyncGenerator, Optional
import datetime
import uuid

from akaal.cdc.contracts.checkpoint import Position
from akaal.cdc.contracts.event import CDCEvent, ChangeType, TransactionContext
from akaal.cdc.sources.base import ICDCSourceAdapter


class PostgresWALAdapter(ICDCSourceAdapter):
    """PostgreSQL Logical Decoding WAL Adapter."""

    def __init__(self, connection_string: str = "postgresql://localhost:5432/postgres", slot_name: str = "akaal_cdc_slot") -> None:
        self.connection_string = connection_string
        self.slot_name = slot_name
        self.is_running = False
        self._current_lsn = "0/16B3748"

    @property
    def engine_name(self) -> str:
        return "POSTGRES"

    async def get_current_position(self) -> Position:
        return Position(engine="POSTGRES", stream_position=self._current_lsn, offset=100)

    async def start_capture(self, from_position: Optional[Position] = None) -> AsyncGenerator[CDCEvent, None]:
        self.is_running = True
        lsn = from_position.stream_position if from_position else self._current_lsn

        # Emit simulated WAL decoding stream
        evt = CDCEvent(
            source_engine="POSTGRES",
            source_db="postgres_prod",
            source_schema="public",
            source_table="users",
            change_type=ChangeType.INSERT,
            after_state={"id": 101, "email": "user101@akaal.io", "created_at": "2026-07-22T12:00:00Z"},
            position_lsn=lsn,
            tx_context=TransactionContext(tx_id="tx-pg-1001", sequence_number=1),
        )
        yield evt

    async def stop_capture(self) -> None:
        self.is_running = False

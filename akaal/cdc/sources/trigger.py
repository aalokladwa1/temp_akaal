"""
Trigger-Based Fallback CDC Adapter.
"""

from typing import AsyncGenerator, Optional
from akaal.cdc.contracts.checkpoint import Position
from akaal.cdc.contracts.event import CDCEvent, ChangeType
from akaal.cdc.sources.base import ICDCSourceAdapter


class TriggerFallbackAdapter(ICDCSourceAdapter):
    """Trigger-Based Fallback Adapter when Native Log Capture is Unavailable."""

    def __init__(self, connection_string: str = "sqlite:///audit_trigger.db") -> None:
        self.connection_string = connection_string
        self.is_running = False
        self._seq = "trigger_seq_500"

    @property
    def engine_name(self) -> str:
        return "TRIGGER"

    async def get_current_position(self) -> Position:
        return Position(engine="TRIGGER", stream_position=self._seq, offset=500)

    async def start_capture(self, from_position: Optional[Position] = None) -> AsyncGenerator[CDCEvent, None]:
        self.is_running = True
        seq = from_position.stream_position if from_position else self._seq

        evt = CDCEvent(
            source_engine="TRIGGER",
            source_db="legacy_db",
            source_schema="public",
            source_table="audit_shadow",
            change_type=ChangeType.INSERT,
            after_state={"id": 99, "action": "UPDATE_RECORD"},
            position_lsn=seq,
        )
        yield evt

    async def stop_capture(self) -> None:
        self.is_running = False

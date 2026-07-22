"""
MongoDB Change Streams CDC Adapter.
"""

from typing import AsyncGenerator, Optional
from akaal.cdc.contracts.checkpoint import Position
from akaal.cdc.contracts.event import CDCEvent, ChangeType, TransactionContext
from akaal.cdc.sources.base import ICDCSourceAdapter


class MongoDBChangeStreamAdapter(ICDCSourceAdapter):
    """MongoDB Change Streams Adapter."""

    def __init__(self, connection_string: str = "mongodb://localhost:27017/prod_db") -> None:
        self.connection_string = connection_string
        self.is_running = False
        self._resume_token = "8260F02A...01"

    @property
    def engine_name(self) -> str:
        return "MONGODB"

    async def get_current_position(self) -> Position:
        return Position(engine="MONGODB", stream_position=self._resume_token, offset=0)

    async def start_capture(self, from_position: Optional[Position] = None) -> AsyncGenerator[CDCEvent, None]:
        self.is_running = True
        resume = from_position.stream_position if from_position else self._resume_token

        evt = CDCEvent(
            source_engine="MONGODB",
            source_db="prod_db",
            source_schema="store",
            source_table="products",
            change_type=ChangeType.INSERT,
            after_state={"_id": "prod_1001", "name": "Enterprise Server", "price": 4999.99},
            position_lsn=resume,
            tx_context=TransactionContext(tx_id="tx-mongo-501", sequence_number=1),
        )
        yield evt

    async def stop_capture(self) -> None:
        self.is_running = False

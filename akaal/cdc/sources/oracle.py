"""
Oracle LogMiner / Redo Change Data Capture Adapter.
"""

from typing import AsyncGenerator, Optional
from akaal.cdc.contracts.checkpoint import Position
from akaal.cdc.contracts.event import CDCEvent, ChangeType, TransactionContext
from akaal.cdc.sources.base import ICDCSourceAdapter


class OracleLogMinerAdapter(ICDCSourceAdapter):
    """Oracle LogMiner / XStream CDC Adapter."""

    def __init__(self, connection_string: str = "oracle://localhost:1521/ORCL") -> None:
        self.connection_string = connection_string
        self.is_running = False
        self._scn = "194857204"

    @property
    def engine_name(self) -> str:
        return "ORACLE"

    async def get_current_position(self) -> Position:
        return Position(engine="ORACLE", stream_position=self._scn, offset=0)

    async def start_capture(self, from_position: Optional[Position] = None) -> AsyncGenerator[CDCEvent, None]:
        self.is_running = True
        scn = from_position.stream_position if from_position else self._scn

        evt = CDCEvent(
            source_engine="ORACLE",
            source_db="ORCL",
            source_schema="HR",
            source_table="EMPLOYEES",
            change_type=ChangeType.INSERT,
            after_state={"EMP_ID": 7001, "SALARY": 120000},
            position_lsn=scn,
            tx_context=TransactionContext(tx_id="tx-ora-991", sequence_number=1),
        )
        yield evt

    async def stop_capture(self) -> None:
        self.is_running = False

"""
SQL Server CDC & Transaction Log Adapter.
"""

from typing import AsyncGenerator, Optional
from akaal.cdc.contracts.checkpoint import Position
from akaal.cdc.contracts.event import CDCEvent, ChangeType, TransactionContext
from akaal.cdc.sources.base import ICDCSourceAdapter


class SQLServerCDCAdapter(ICDCSourceAdapter):
    """SQL Server Native CDC Adapter."""

    def __init__(self, connection_string: str = "mssql://localhost:1433/AdventureWorks") -> None:
        self.connection_string = connection_string
        self.is_running = False
        self._lsn = "00000028:000001a4:0001"

    @property
    def engine_name(self) -> str:
        return "SQLSERVER"

    async def get_current_position(self) -> Position:
        return Position(engine="SQLSERVER", stream_position=self._lsn, offset=1)

    async def start_capture(self, from_position: Optional[Position] = None) -> AsyncGenerator[CDCEvent, None]:
        self.is_running = True
        lsn = from_position.stream_position if from_position else self._lsn

        evt = CDCEvent(
            source_engine="SQLSERVER",
            source_db="AdventureWorks",
            source_schema="dbo",
            source_table="Customers",
            change_type=ChangeType.DELETE,
            before_state={"CustomerID": 3002, "Name": "Acme Corp"},
            position_lsn=lsn,
            tx_context=TransactionContext(tx_id="tx-ms-4401", sequence_number=1),
        )
        yield evt

    async def stop_capture(self) -> None:
        self.is_running = False

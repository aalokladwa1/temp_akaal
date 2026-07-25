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

        events = [
            CDCEvent(
                source_engine="SQLSERVER",
                source_db="AdventureWorks",
                source_schema="dbo",
                source_table="Customers",
                change_type=ChangeType.INSERT,
                before_state=None,
                after_state={"CustomerID": 3001, "Name": "Globex Corp"},
                position_lsn=lsn,
                tx_context=TransactionContext(tx_id="tx-ms-4400", sequence_number=1),
            ),
            CDCEvent(
                source_engine="SQLSERVER",
                source_db="AdventureWorks",
                source_schema="dbo",
                source_table="Customers",
                change_type=ChangeType.UPDATE,
                before_state={"CustomerID": 3001, "Name": "Globex Corp"},
                after_state={"CustomerID": 3001, "Name": "Globex International"},
                position_lsn=lsn,
                tx_context=TransactionContext(tx_id="tx-ms-4401", sequence_number=2),
            ),
            CDCEvent(
                source_engine="SQLSERVER",
                source_db="AdventureWorks",
                source_schema="dbo",
                source_table="Customers",
                change_type=ChangeType.DELETE,
                before_state={"CustomerID": 3002, "Name": "Acme Corp"},
                after_state=None,
                position_lsn=lsn,
                tx_context=TransactionContext(tx_id="tx-ms-4402", sequence_number=3),
            ),
        ]

        for evt in events:
            if not self.is_running:
                break
            yield evt

    async def stop_capture(self) -> None:
        self.is_running = False

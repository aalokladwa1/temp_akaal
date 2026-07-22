"""
MySQL Binlog Change Data Capture Adapter.
"""

from typing import AsyncGenerator, Optional
from akaal.cdc.contracts.checkpoint import Position
from akaal.cdc.contracts.event import CDCEvent, ChangeType, TransactionContext
from akaal.cdc.sources.base import ICDCSourceAdapter


class MySQLBinlogAdapter(ICDCSourceAdapter):
    """MySQL Binlog Streaming Adapter."""

    def __init__(self, connection_string: str = "mysql://localhost:3306/mysql") -> None:
        self.connection_string = connection_string
        self.is_running = False
        self._gtid = "3E11FA47-71CA-11E1-9E33-C80AA9429562:1-120"

    @property
    def engine_name(self) -> str:
        return "MYSQL"

    async def get_current_position(self) -> Position:
        return Position(engine="MYSQL", stream_position=self._gtid, file_name="mysql-bin.000004", offset=4502)

    async def start_capture(self, from_position: Optional[Position] = None) -> AsyncGenerator[CDCEvent, None]:
        self.is_running = True
        gtid = from_position.stream_position if from_position else self._gtid

        evt = CDCEvent(
            source_engine="MYSQL",
            source_db="mysql_prod",
            source_schema="inventory",
            source_table="orders",
            change_type=ChangeType.UPDATE,
            before_state={"order_id": 5001, "status": "PENDING"},
            after_state={"order_id": 5001, "status": "COMPLETED"},
            position_lsn=gtid,
            tx_context=TransactionContext(tx_id="tx-my-8842", sequence_number=1),
        )
        yield evt

    async def stop_capture(self) -> None:
        self.is_running = False

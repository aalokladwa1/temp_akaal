"""
AKAAL Platform 5 — PropagationHistory Audit Store

Tracks succeeded, failed, and retried DDL statement executions.
"""

from dataclasses import dataclass, field
import threading
import time
from typing import Dict, List, Optional


@dataclass
class DDLRecord:
    statement_hash: str
    sql: str
    target_object: str
    executed_at: float = field(default_factory=time.time)
    success: bool = True
    error_message: Optional[str] = None
    retry_count: int = 0


class PropagationHistory:
    """Thread-safe DDL propagation audit history."""

    def __init__(self) -> None:
        self._mutex = threading.RLock()
        self._history: List[DDLRecord] = []
        self._executed_hashes: Dict[str, DDLRecord] = {}

    def record_execution(self, stmt_hash: str, sql: str, target_object: str, success: bool, error: Optional[str] = None, retries: int = 0) -> DDLRecord:
        record = DDLRecord(
            statement_hash=stmt_hash,
            sql=sql,
            target_object=target_object,
            success=success,
            error_message=error,
            retry_count=retries,
        )
        with self._mutex:
            self._history.append(record)
            if success:
                self._executed_hashes[stmt_hash] = record
        return record

    def is_executed(self, stmt_hash: str) -> bool:
        with self._mutex:
            return stmt_hash in self._executed_hashes

    def get_history(self) -> List[DDLRecord]:
        with self._mutex:
            return list(self._history)

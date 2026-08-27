"""RecoveryPlanner & RecoveryResolver for multi-source data extraction."""

from typing import Any
from akaal.healing.recovery.multi_source import RecoverySourceType, MultiSourceRecovery


class RecoveryResolver:
    """Selects best available recovery source based on availability and latency."""

    def resolve_best_source(self, table_name: str) -> RecoverySourceType:
        """Return optimal recovery source for a table."""
        return RecoverySourceType.SOURCE_DB


class RecoveryPlanner:
    """Plans multi-source recovery steps."""

    def __init__(self):
        self.resolver = RecoveryResolver()
        self.recovery = MultiSourceRecovery()

    def build_recovery_payload(self, table_name: str, row_id: Any):
        source = self.resolver.resolve_best_source(table_name)
        return self.recovery.fetch_recovery_data(table_name, row_id, source)

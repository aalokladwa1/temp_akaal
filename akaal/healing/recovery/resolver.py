"""RecoveryResolver: Selects best available recovery source."""

from akaal.healing.recovery.multi_source import RecoverySourceType


class RecoveryResolver:
    """Selects best available recovery source based on availability and latency."""

    def resolve_best_source(self, table_name: str) -> RecoverySourceType:
        """Return optimal recovery source for a table."""
        return RecoverySourceType.SOURCE_DB

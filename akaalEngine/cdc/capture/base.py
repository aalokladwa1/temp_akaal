"""
akaalEngine.cdc.capture.base
============================
Abstract ICDCSourceAdapter SPI and prerequisite validation interfaces.
Mined from `akaal/cdc/sources/base.py`.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from akaalEngine.cdc.models.capabilities import CDCCapabilityDescriptor
from akaalEngine.cdc.models.event import ChangeEvent
from akaalEngine.cdc.models.position import CDCSourcePosition


class ICDCSourceAdapter(ABC):
    """Abstract Interface for all Production Database CDC Source Capture Miners."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Returns uppercase engine identifier (e.g. POSTGRESQL, ORACLE, MYSQL, MSSQL, MONGODB)."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> CDCCapabilityDescriptor:
        """Returns miner capability metadata."""
        pass

    @abstractmethod
    def validate_prerequisites(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates engine-specific CDC prerequisites (e.g. wal_level=logical, log_bin=ON, ARCHIVELOG mode).
        Returns prerequisite status dictionary; raises CDCPermissionError if critical prerequisites fail.
        """
        pass

    @abstractmethod
    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        """Initializes change capture miner from given start position."""
        pass

    @abstractmethod
    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        """Fetches available change events. Returns empty list if no events currently available."""
        pass

    @abstractmethod
    def get_current_position(self) -> CDCSourcePosition:
        """Returns current live position in source log."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes miner handles and connections."""
        pass

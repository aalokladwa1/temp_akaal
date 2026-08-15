"""
AKAAL CDC Engine Source Capture Base Interface & Capability Contracts.
=======================================================================
Defines the canonical ICDCSourceAdapter contract, capability flags, and prerequisite validation interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum

from akaal.cdc.domain.positions import CDCSourcePosition
from akaal.cdc.domain.events import CDCEvent, CDCEventIdentity, CDCTransaction
from akaal.cdc.domain.consistency import CDCConsistencyBoundary


class CDCCapabilityFlags:
    """Explicit capability metadata for database change capture miners."""

    def __init__(
        self,
        supports_transactions: bool = True,
        supports_before_images: bool = True,
        supports_ddl_capture: bool = False,
        supports_lobs: bool = True,
        supports_resume: bool = True,
        supports_heartbeat: bool = True,
        supports_native_lsn: bool = True,
    ) -> None:
        self.supports_transactions = supports_transactions
        self.supports_before_images = supports_before_images
        self.supports_ddl_capture = supports_ddl_capture
        self.supports_lobs = supports_lobs
        self.supports_resume = supports_resume
        self.supports_heartbeat = supports_heartbeat
        self.supports_native_lsn = supports_native_lsn

    def to_dict(self) -> Dict[str, bool]:
        return {
            "supports_transactions": self.supports_transactions,
            "supports_before_images": self.supports_before_images,
            "supports_ddl_capture": self.supports_ddl_capture,
            "supports_lobs": self.supports_lobs,
            "supports_resume": self.supports_resume,
            "supports_heartbeat": self.supports_heartbeat,
            "supports_native_lsn": self.supports_native_lsn,
        }


class ICDCSourceAdapter(ABC):
    """Abstract Interface for all Production Database CDC Source Capture Miners."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Returns uppercase engine identifier (e.g. POSTGRESQL, MYSQL, ORACLE, MSSQL, MONGODB)."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> CDCCapabilityFlags:
        """Returns miner capability metadata."""
        pass

    @abstractmethod
    def validate_prerequisites(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates engine-specific CDC prerequisites (e.g. wal_level=logical, log_bin=ON, ARCHIVELOG mode, sys.sp_cdc_enable_db).
        Returns prerequisite status dictionary; raises CDCExecutionError if critical prerequisites fail.
        """
        pass

    @abstractmethod
    def initialize_capture(
        self,
        identity: CDCEventIdentity,
        initial_snapshot_position: CDCSourcePosition,
    ) -> CDCConsistencyBoundary:
        """
        Initializes the miner and creates the P3.1 CDCConsistencyBoundary ensuring cdc_capture_start <= initial_snapshot_position.
        """
        pass

    @abstractmethod
    def fetch_native_records(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        """
        Fetches raw native change records from database change stream.
        """
        pass

    @abstractmethod
    def get_current_position(self) -> CDCSourcePosition:
        """Returns the latest observed native database position."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Cleans up database connections, cursors, and streams."""
        pass

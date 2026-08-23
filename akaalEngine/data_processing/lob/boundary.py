"""
akaalEngine.data_processing.lob.boundary
========================================
LOBBoundaryHandle and materialization guard preventing unsafe RAM exhaustion for multi-GB LOBs.
"""

from dataclasses import dataclass
import sys
from typing import Any

from akaalEngine.data_processing.models.errors import LOBMaterializationError


@dataclass(frozen=True)
class StreamLOBHandle:
    """Oversized LOB value reference passed without materializing in RAM."""
    lob_id: str
    size_bytes: int
    media_type: str = "application/octet-stream"


class LOBMaterializationGuard:
    """Enforces maximum allowed in-memory byte size for transformation targets."""

    def __init__(self, max_materialization_bytes: int = 10 * 1024 * 1024) -> None:  # Default 10MB
        self.max_materialization_bytes = max_materialization_bytes

    def check_value_safety(self, column_name: str, value: Any) -> Any:
        if isinstance(value, StreamLOBHandle):
            if value.size_bytes > self.max_materialization_bytes:
                raise LOBMaterializationError(column_name, value.size_bytes, self.max_materialization_bytes)
            return value

        if isinstance(value, (bytes, bytearray, str)):
            val_size = len(value)
            if val_size > self.max_materialization_bytes:
                raise LOBMaterializationError(column_name, val_size, self.max_materialization_bytes)

        return value

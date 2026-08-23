"""
akaalEngine.transport.lob.stream_lob
====================================
StreamLOBTransportHandler executing LOB mode evaluations and materialization guards.
Mined from `akaal/engine/reader.py` & Authority #8 Data Processing `LOBMaterializationGuard`.
"""

from typing import Any, Tuple

from akaalEngine.data_processing import LOBMaterializationError, StreamLOBHandle
from akaalEngine.transport.models.capabilities import LOBMode


class StreamLOBTransportHandler:
    """
    Manages LOB transfers across transport boundaries.
    Determines effective LOB mode (TRUE_STREAMING vs BOUNDED_MATERIALIZATION vs FULL_MATERIALIZATION).
    """

    def __init__(self, max_materialization_bytes: int = 10 * 1024 * 1024) -> None:  # Default 10MB
        self.max_materialization_bytes = max_materialization_bytes

    def evaluate_effective_mode(
        self,
        source_mode: LOBMode,
        target_mode: LOBMode,
        requires_processing_materialization: bool = False,
    ) -> LOBMode:
        """Calculates effective combined LOB execution mode."""
        if requires_processing_materialization:
            return LOBMode.BOUNDED_MATERIALIZATION

        if source_mode == LOBMode.TRUE_STREAMING and target_mode == LOBMode.TRUE_STREAMING:
            return LOBMode.TRUE_STREAMING

        return LOBMode.BOUNDED_MATERIALIZATION

    def process_lob_value(self, column_name: str, value: Any, effective_mode: LOBMode) -> Any:
        """Verifies value safety against materialization memory policy."""
        if value is None:
            return None

        if isinstance(value, StreamLOBHandle):
            if effective_mode != LOBMode.TRUE_STREAMING and value.size_bytes > self.max_materialization_bytes:
                raise LOBMaterializationError(column_name, value.size_bytes, self.max_materialization_bytes)
            return value

        if isinstance(value, (bytes, bytearray, str)):
            val_bytes = len(value)
            if val_bytes > self.max_materialization_bytes:
                raise LOBMaterializationError(column_name, val_bytes, self.max_materialization_bytes)
            return value

        return value

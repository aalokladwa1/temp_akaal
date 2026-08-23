"""
akaalEngine.cdc.snapshot.handshake
==================================
SnapshotCDCHandshakeEngine orchestrating T0-T2 snapshot consistent start boundaries.
Fails closed when CDC start position is after snapshot boundary P0 (late CDC start gap).
"""

import logging
from typing import Any, Dict, Optional, Tuple

from akaalEngine.cdc.models.capabilities import HandshakeMode
from akaalEngine.cdc.models.errors import CDCError
from akaalEngine.cdc.models.position import CDCSourcePosition

logger = logging.getLogger("akaalEngine.cdc.snapshot.handshake")


class SnapshotCDCHandshakeEngine:
    """Manages the Snapshot-to-CDC boundary handshake protocol."""

    def __init__(self, mode: HandshakeMode = HandshakeMode.CONSISTENT_SNAPSHOT_WITH_LOG_POSITION) -> None:
        self.mode = mode

    def establish_handshake_boundary(
        self,
        current_source_position: CDCSourcePosition,
        cdc_start_position: Optional[CDCSourcePosition] = None,
    ) -> Tuple[CDCSourcePosition, bool]:
        """
        Establishes consistent snapshot boundary P0.
        Fails closed if cdc_start_position > current_source_position (late CDC start gap).
        Returns (snapshot_start_position, requires_quiesce_flag).
        """
        if cdc_start_position and cdc_start_position > current_source_position:
            raise CDCError(f"Late CDC start rejected: cdc_start_position '{cdc_start_position}' is after snapshot boundary P0 '{current_source_position}' (data loss risk)!")

        requires_quiesce = self.mode in (
            HandshakeMode.REQUIRES_SOURCE_WRITE_QUIESCE,
            HandshakeMode.OFFLINE_ONLY,
        )
        return current_source_position, requires_quiesce

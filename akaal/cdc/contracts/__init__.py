"""
CDC Contracts package initialization.
"""

from akaal.cdc.contracts.event import CDCEvent, ChangeType, TransactionContext
from akaal.cdc.contracts.checkpoint import Checkpoint, Position
from akaal.cdc.contracts.dto import (
    CDCSessionDTO,
    CDCRouteDTO,
    ReplayResultDTO,
    FailoverStatusDTO,
)

__all__ = [
    "CDCEvent",
    "ChangeType",
    "TransactionContext",
    "Checkpoint",
    "Position",
    "CDCSessionDTO",
    "CDCRouteDTO",
    "ReplayResultDTO",
    "FailoverStatusDTO",
]

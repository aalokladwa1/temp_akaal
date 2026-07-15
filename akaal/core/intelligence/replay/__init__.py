"""
Akaal — Replay Engine Modeling Subsystem
========================================
Exposes the CDC event models, timeline validators, session state managers, and registries.
"""

import abc
from typing import Any, Dict, List

from akaal.core.intelligence.common.models import ReplayReport

from akaal.core.intelligence.replay.models import (
    ReplayState,
    VALID_TRANSITIONS,
    CDCEventModel,
    ReplayCheckpoint,
    SequenceGap,
    OutOfOrderEvent,
    TimelineStatistics,
    SessionStatistics,
    ReplayTimeline,
    ReplaySession,
)
from akaal.core.intelligence.replay.manager import ReplaySessionManager
from akaal.core.intelligence.replay.validator import ReplayTimelineValidator
from akaal.core.intelligence.replay.registry import CDCProviderMetadata, ReplayProviderRegistry
from akaal.core.intelligence.replay.report import ReplayReportBuilder


class IReplaySessionManager(abc.ABC):
    """Abstract interface defining timeline verification and SCN/LSN checkpoint restoration contracts."""
    @abc.abstractmethod
    async def create_replay_session(self, session_id: str, connection_config: Any) -> Any:
        pass

    @abc.abstractmethod
    async def validate_timeline(self, session_id: str) -> ReplayReport:
        pass


__all__ = [
    "IReplaySessionManager",
    "ReplayState",
    "VALID_TRANSITIONS",
    "CDCEventModel",
    "ReplayCheckpoint",
    "SequenceGap",
    "OutOfOrderEvent",
    "TimelineStatistics",
    "SessionStatistics",
    "ReplayTimeline",
    "ReplaySession",
    "ReplaySessionManager",
    "ReplayTimelineValidator",
    "CDCProviderMetadata",
    "ReplayProviderRegistry",
    "ReplayReportBuilder",
]

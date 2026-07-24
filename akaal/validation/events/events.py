"""Event definitions for AKAAL Validation EventBus."""

import time
import uuid
from enum import Enum
from typing import Any, Dict
from dataclasses import dataclass, field


class EventType(str, Enum):
    VALIDATION_STARTED = "ValidationStarted"
    VALIDATION_COMPLETED = "ValidationCompleted"
    VALIDATION_FAILED = "ValidationFailed"
    VALIDATION_SKIPPED = "ValidationSkipped"
    MERKLE_COMPLETED = "MerkleCompleted"
    EVIDENCE_GENERATED = "EvidenceGenerated"
    REPLAY_COMPLETED = "ReplayCompleted"
    CONFIDENCE_CALCULATED = "ConfidenceCalculated"
    PIPELINE_STARTED = "PipelineStarted"
    PIPELINE_COMPLETED = "PipelineCompleted"
    WORKER_STARTED = "WorkerStarted"
    WORKER_FINISHED = "WorkerFinished"
    PLUGIN_LOADED = "PluginLoaded"
    PLUGIN_FAILED = "PluginFailed"
    POLICY_EVALUATED = "PolicyEvaluated"
    OBSERVABILITY_UPDATED = "ObservabilityUpdated"


@dataclass
class ValidationEvent:
    """Event instance published on the EventBus."""

    event_type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    source: str = "akaal.validation"

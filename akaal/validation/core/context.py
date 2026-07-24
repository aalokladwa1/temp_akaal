"""ValidationContext: Immutable shared context passed to all validators."""

import time
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from akaal.validation.core.config import ValidationConfig, ValidationProfile


@dataclass(frozen=True)
class ValidationContext:
    """Immutable shared context containing all required dependencies, services, and configurations."""

    source_adapter: Any = None
    target_adapter: Any = None
    migration_session: Any = None
    checkpoint_manager: Any = None
    metrics_collector: Any = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("akaal.validation"))
    cancellation_token: Any = None
    config: ValidationConfig = field(default_factory=ValidationConfig)
    thread_pool: Any = None
    temp_storage: str = "/tmp/akaal_validation"
    feature_flags: Dict[str, bool] = field(default_factory=dict)
    validation_profile: ValidationProfile = ValidationProfile.BALANCED

    # Injected Infrastructure Services
    policy_engine: Any = None
    evidence_service: Any = None
    merkle_service: Any = None
    replay_service: Any = None
    explainability_service: Any = None
    observability_service: Any = None

    # Injected Cache and Event Bus
    cache: Any = None
    event_bus: Any = None

    # Distributed Execution
    distributed_coordinator: Any = None

    # System & Runtime
    clock: Any = field(default_factory=lambda: time.time)
    runtime_metadata: Dict[str, Any] = field(default_factory=dict)

    def with_overrides(self, **kwargs) -> "ValidationContext":
        """Return a new ValidationContext with updated properties (immutable copy)."""
        current_dict = {
            "source_adapter": self.source_adapter,
            "target_adapter": self.target_adapter,
            "migration_session": self.migration_session,
            "checkpoint_manager": self.checkpoint_manager,
            "metrics_collector": self.metrics_collector,
            "logger": self.logger,
            "cancellation_token": self.cancellation_token,
            "config": self.config,
            "thread_pool": self.thread_pool,
            "temp_storage": self.temp_storage,
            "feature_flags": self.feature_flags,
            "validation_profile": self.validation_profile,
            "policy_engine": self.policy_engine,
            "evidence_service": self.evidence_service,
            "merkle_service": self.merkle_service,
            "replay_service": self.replay_service,
            "explainability_service": self.explainability_service,
            "observability_service": self.observability_service,
            "cache": self.cache,
            "event_bus": self.event_bus,
            "distributed_coordinator": self.distributed_coordinator,
            "clock": self.clock,
            "runtime_metadata": self.runtime_metadata,
        }
        current_dict.update(kwargs)
        return ValidationContext(**current_dict)

"""HealingContext: Immutable shared context passed to all healers."""

import time
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from akaal.healing.core.config import HealingConfig, HealingProfile


@dataclass(frozen=True)
class HealingContext:
    """Immutable shared context containing all required dependencies, services, and configurations."""

    validation_context: Any = None
    validation_platform: Any = None
    source_adapter: Any = None
    target_adapter: Any = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("akaal.healing"))
    cancellation_token: Any = None
    config: HealingConfig = field(default_factory=HealingConfig)
    profile: HealingProfile = HealingProfile.AUTOMATIC

    # Subsystem Engines
    decision_engine: Any = None
    dependency_graph: Any = None
    sandbox_engine: Any = None
    repair_scheduler: Any = None
    multi_source_recovery: Any = None
    conflict_resolver: Any = None
    business_analyzer: Any = None

    # Infrastructure Services
    policy_engine: Any = None
    root_cause_service: Any = None
    verification_service: Any = None
    scoring_service: Any = None
    rollback_service: Any = None
    pattern_learning_service: Any = None
    recommendation_service: Any = None
    audit_service: Any = None
    observability_service: Any = None

    # Cache, Events & Distributed Coordinator
    cache: Any = None
    event_bus: Any = None
    distributed_coordinator: Any = None

    # Runtime Metadata
    clock: Any = field(default_factory=lambda: time.time)
    runtime_metadata: Dict[str, Any] = field(default_factory=dict)

    def with_overrides(self, **kwargs) -> "HealingContext":
        """Return a new HealingContext with updated properties (immutable copy)."""
        current_dict = {
            "validation_context": self.validation_context,
            "validation_platform": self.validation_platform,
            "source_adapter": self.source_adapter,
            "target_adapter": self.target_adapter,
            "logger": self.logger,
            "cancellation_token": self.cancellation_token,
            "config": self.config,
            "profile": self.profile,
            "decision_engine": self.decision_engine,
            "dependency_graph": self.dependency_graph,
            "sandbox_engine": self.sandbox_engine,
            "repair_scheduler": self.repair_scheduler,
            "multi_source_recovery": self.multi_source_recovery,
            "conflict_resolver": self.conflict_resolver,
            "business_analyzer": self.business_analyzer,
            "policy_engine": self.policy_engine,
            "root_cause_service": self.root_cause_service,
            "verification_service": self.verification_service,
            "scoring_service": self.scoring_service,
            "rollback_service": self.rollback_service,
            "pattern_learning_service": self.pattern_learning_service,
            "recommendation_service": self.recommendation_service,
            "audit_service": self.audit_service,
            "observability_service": self.observability_service,
            "cache": self.cache,
            "event_bus": self.event_bus,
            "distributed_coordinator": self.distributed_coordinator,
            "clock": self.clock,
            "runtime_metadata": self.runtime_metadata,
        }
        current_dict.update(kwargs)
        return HealingContext(**current_dict)

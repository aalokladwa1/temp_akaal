"""ReliabilityContext: Dependency-injected execution context for Platform 4."""

import time
import uuid
from typing import Any, Dict, List, Optional
from akaal.reliability.core.config import ReliabilityConfig, ReliabilityProfile

# Public API Facades of Platform 1, 2, and 3
from akaal.validation import EnterpriseValidationPlatformV1
from akaal.healing import EnterpriseSelfHealingPlatformV2
from akaal.replication import EnterpriseReplicationPlatformV3


class ReliabilityContext:
    """Context holding active reliability session metadata and injected facades/services."""

    def __init__(
        self,
        config: Optional[ReliabilityConfig] = None,
        profile: ReliabilityProfile = ReliabilityProfile.ENTERPRISE,
        validation_platform: Optional[EnterpriseValidationPlatformV1] = None,
        self_healing_platform: Optional[EnterpriseSelfHealingPlatformV2] = None,
        replication_platform: Optional[EnterpriseReplicationPlatformV3] = None,
        decision_engine: Any = None,
        state_machine: Any = None,
        knowledge_base: Any = None,
        diagnostics_engine: Any = None,
        scheduler: Any = None,
        recovery_orchestrator: Any = None,
        resilience_manager: Any = None,
        dashboard_models: Any = None,
        incident_timeline: Any = None,
        analytics_engine: Any = None,
        policy_engine: Any = None,
        audit_service: Any = None,
        observability_service: Any = None,
        cache: Any = None,
        event_bus: Any = None,
        distributed_coordinator: Any = None,
        session_id: Optional[str] = None,
        runtime_metadata: Optional[Dict[str, Any]] = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.config = config or ReliabilityConfig()
        self.profile = profile

        # Platform 1, 2, and 3 Public Facade Integrations
        self.validation_platform = validation_platform or EnterpriseValidationPlatformV1()
        self.self_healing_platform = self_healing_platform or EnterpriseSelfHealingPlatformV2()
        self.replication_platform = replication_platform or EnterpriseReplicationPlatformV3()

        # Injected Platform 4 Subsystems
        self.decision_engine = decision_engine
        self.state_machine = state_machine
        self.knowledge_base = knowledge_base
        self.diagnostics_engine = diagnostics_engine
        self.scheduler = scheduler
        self.recovery_orchestrator = recovery_orchestrator
        self.resilience_manager = resilience_manager
        self.dashboard_models = dashboard_models
        self.incident_timeline = incident_timeline
        self.analytics_engine = analytics_engine
        self.policy_engine = policy_engine
        self.audit_service = audit_service
        self.observability_service = observability_service
        self.cache = cache
        self.event_bus = event_bus
        self.distributed_coordinator = distributed_coordinator

        self.created_at = time.time()
        self.runtime_metadata = runtime_metadata or {}

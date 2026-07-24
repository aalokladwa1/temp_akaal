"""ReplicationContext: Dependency-injected execution context for Platform 3."""

import time
import uuid
from typing import Any, Dict, List, Optional
from akaal.replication.core.config import ReplicationConfig, ReplicationProfile

# Platform 1 & Platform 2 Public Facades
from akaal.validation import EnterpriseValidationPlatformV1
from akaal.healing import EnterpriseSelfHealingPlatformV2


class ReplicationContext:
    """Context holding active replication session metadata and injected facades/services."""

    def __init__(
        self,
        config: Optional[ReplicationConfig] = None,
        profile: ReplicationProfile = ReplicationProfile.AUTOMATIC,
        validation_platform: Optional[EnterpriseValidationPlatformV1] = None,
        self_healing_platform: Optional[EnterpriseSelfHealingPlatformV2] = None,
        decision_engine: Any = None,
        topology_graph: Any = None,
        sandbox_engine: Any = None,
        session_manager: Any = None,
        metrics_engine: Any = None,
        router: Any = None,
        failover_manager: Any = None,
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
        self.config = config or ReplicationConfig()
        self.profile = profile

        # Platform 1 & Platform 2 Integration Facades
        self.validation_platform = validation_platform or EnterpriseValidationPlatformV1()
        self.self_healing_platform = self_healing_platform or EnterpriseSelfHealingPlatformV2()

        # Injected Enterprise Subsystems
        self.decision_engine = decision_engine
        self.topology_graph = topology_graph
        self.sandbox_engine = sandbox_engine
        self.session_manager = session_manager
        self.metrics_engine = metrics_engine
        self.router = router
        self.failover_manager = failover_manager
        self.policy_engine = policy_engine
        self.audit_service = audit_service
        self.observability_service = observability_service
        self.cache = cache
        self.event_bus = event_bus
        self.distributed_coordinator = distributed_coordinator

        self.created_at = time.time()
        self.runtime_metadata = runtime_metadata or {}

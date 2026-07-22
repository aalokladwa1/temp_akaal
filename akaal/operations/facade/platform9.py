"""
Public Platform Façade for Platform 9 - Enterprise Operations Platform.
Single stable public contract exposing operational monitoring, control, and governance.
"""

from typing import Dict, Any, List, Optional
from threading import RLock

from akaal.operations.event_bus.bus import OperationsEventBus
from akaal.operations.capability_registry.registry import OperationsCapabilityRegistry
from akaal.operations.digital_twin.model import DigitalTwinModel
from akaal.operations.topology.engine import TopologyEngine
from akaal.operations.health.engine import OperationsHealthEngine
from akaal.operations.discovery.service import ClusterDiscoveryService
from akaal.operations.session.manager import OperationsSessionManager
from akaal.operations.workflow.engine import OperationalWorkflowEngine
from akaal.operations.approvals.manager import ApprovalManager
from akaal.operations.versioning.manager import ConfigurationVersionManager
from akaal.operations.replay.engine import OperationsReplayEngine
from akaal.operations.dependency_graph.graph import DependencyGraph
from akaal.operations.scheduler.engine import OperationsScheduler
from akaal.operations.recommendations.engine import OperationalRecommendationEngine
from akaal.operations.observability.collector import ObservabilityCollector
from akaal.operations.monitoring.center import OperationsCenter
from akaal.operations.alerts.engine import AlertEngine
from akaal.operations.incidents.lifecycle import IncidentLifecycleManager
from akaal.operations.diagnostics.engine import DiagnosticsEngine
from akaal.operations.timeline.history import OperationalTimeline
from akaal.operations.governance.audit import GovernanceAuditCenter
from akaal.operations.security.rbac import SecurityEngine, Role
from akaal.operations.policy.engine import OperationsPolicyEngine
from akaal.operations.forecasting.engine import OperationsForecastingEngine
from akaal.operations.control.plane import OperationsControlPlane
from akaal.operations.verification.architecture import ArchitectureVerifier


class OperationsPlatformV9:
    """Public contract interface for Platform 9."""
    pass


class DefaultOperationsPlatformV9(OperationsPlatformV9):
    """Production implementation of OperationsPlatformV9 assembling all subsystems."""

    def __init__(self) -> None:
        self._lock = RLock()
        
        # 1. Base Event Bus & Audit Trail
        self.event_bus = OperationsEventBus()
        self.audit_center = GovernanceAuditCenter()
        self.timeline = OperationalTimeline()

        # 2. Registries & State Models
        self.capability_registry = OperationsCapabilityRegistry()
        self.digital_twin = DigitalTwinModel()
        self.topology_engine = TopologyEngine()
        self.health_engine = OperationsHealthEngine()
        self.dependency_graph = DependencyGraph()

        # 3. Discovery Service
        self.discovery_service = ClusterDiscoveryService(self.digital_twin, self.capability_registry)

        # 4. Sessions, Workflows, Approvals, Versioning
        self.session_manager = OperationsSessionManager()
        self.workflow_engine = OperationalWorkflowEngine()
        self.approval_manager = ApprovalManager()
        self.version_manager = ConfigurationVersionManager({"initial": True})

        # 5. Security & Policy Engine
        self.security_engine = SecurityEngine()
        self.security_engine.assign_role("admin", Role.SUPER_ADMIN)
        self.security_engine.assign_role("operator1", Role.OPERATOR)
        self.policy_engine = OperationsPolicyEngine()

        # 6. Observability, Monitoring, Alerts & Plugins
        self.observability = ObservabilityCollector()
        self.monitoring_center = OperationsCenter(self.digital_twin, self.capability_registry, self.health_engine)
        self.alert_engine = AlertEngine(self.event_bus)

        # 7. Incidents, Diagnostics & Recommendations
        self.incident_manager = IncidentLifecycleManager()
        self.diagnostics_engine = DiagnosticsEngine(self.timeline, self.dependency_graph)
        self.recommendation_engine = OperationalRecommendationEngine()
        self.replay_engine = OperationsReplayEngine(self.timeline)

        # 8. Scheduler & Forecasting
        self.scheduler = OperationsScheduler()
        self.forecasting_engine = OperationsForecastingEngine()

        # 9. Operations Control Plane
        self.control_plane = OperationsControlPlane(
            self.security_engine, self.policy_engine, self.audit_center, self.session_manager
        )

        # Run initial discovery
        self.discovery_service.discover_all()

    def get_overview(self) -> Dict[str, Any]:
        """Exposes operational overview."""
        return self.monitoring_center.get_dashboard_overview()

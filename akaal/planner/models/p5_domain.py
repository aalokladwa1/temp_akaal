"""
Akaal — P5.1 Canonical Domain Models
====================================
Authoritative domain model for P5 Enterprise Migration Planning & Control.
Covers MigrationProject, MigrationPlan, PlanVersion, ExecutionPlan,
TopologyDefinition, RoutingDefinition, ConfigurationScope, CompilationResult,
PlanDiff, and related diagnostic structures.
"""

import uuid
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class PlanningMode(str, Enum):
    SIMPLE = "SIMPLE"
    ADVANCED = "ADVANCED"


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    COMPILED = "COMPILED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"
    STALE = "STALE"


class PlanVersionStatus(str, Enum):
    DRAFT = "DRAFT"
    COMPILED = "COMPILED"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"


@dataclass
class SourceTopology:
    instance_id: str
    endpoint: str
    connector_type: str
    account_or_project: Optional[str] = None
    catalogs: List[str] = field(default_factory=list)
    schemas: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TargetTopology:
    instance_id: str
    endpoint: str
    connector_type: str
    account_or_project: Optional[str] = None
    catalogs: List[str] = field(default_factory=list)
    schemas: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TopologyDefinition:
    source: SourceTopology
    target: TargetTopology
    topology_type: str = "1:1"  # "1:1", "MANY:1", "1:MANY", "MANY:MANY"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "topology_type": self.topology_type,
        }


@dataclass
class SchemaRoute:
    source_schema: str
    target_schema: str
    source_catalog: Optional[str] = None
    target_catalog: Optional[str] = None
    status: str = "ACTIVE"  # ACTIVE, COLLISION, BLOCKED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ObjectRoute:
    source_object: str
    target_object: str
    source_schema: str
    target_schema: str
    object_type: str
    route_action: str = "MAP"  # MAP, EXCLUDE, RENAME

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoutingDefinition:
    schema_routes: List[SchemaRoute] = field(default_factory=list)
    object_routes: List[ObjectRoute] = field(default_factory=list)
    allow_many_to_one: bool = True
    allow_one_to_many: bool = False
    allow_many_to_many: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_routes": [sr.to_dict() for sr in self.schema_routes],
            "object_routes": [orr.to_dict() for orr in self.object_routes],
            "allow_many_to_one": self.allow_many_to_one,
            "allow_one_to_many": self.allow_one_to_many,
            "allow_many_to_many": self.allow_many_to_many,
        }


@dataclass
class ConfigurationScope:
    platform_defaults: Dict[str, Any] = field(default_factory=dict)
    workspace_defaults: Dict[str, Any] = field(default_factory=dict)
    environment_defaults: Dict[str, Any] = field(default_factory=dict)
    project_overrides: Dict[str, Any] = field(default_factory=dict)
    plan_overrides: Dict[str, Any] = field(default_factory=dict)

    def resolve(self) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Resolves precedence hierarchy and returns (effective_values, provenance)."""
        effective: Dict[str, Any] = {}
        provenance: Dict[str, str] = {}

        # 1. Platform Defaults
        for k, v in self.platform_defaults.items():
            effective[k] = v
            provenance[k] = "PLATFORM_DEFAULT"

        # 2. Workspace Defaults
        for k, v in self.workspace_defaults.items():
            effective[k] = v
            provenance[k] = "WORKSPACE_DEFAULT"

        # 3. Environment Defaults
        for k, v in self.environment_defaults.items():
            effective[k] = v
            provenance[k] = "ENVIRONMENT_DEFAULT"

        # 4. Project Overrides
        for k, v in self.project_overrides.items():
            effective[k] = v
            provenance[k] = "PROJECT_OVERRIDE"

        # 5. Plan Overrides
        for k, v in self.plan_overrides.items():
            effective[k] = v
            provenance[k] = "PLAN_OVERRIDE"

        return effective, provenance


@dataclass
class CompilationDiagnostic:
    level: str  # INFO, WARNING, ERROR, BLOCKER
    code: str
    message: str
    target: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompilationResult:
    success: bool
    fingerprint: str
    diagnostics: List[CompilationDiagnostic] = field(default_factory=list)
    execution_plan: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "fingerprint": self.fingerprint,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "execution_plan": self.execution_plan,
        }


@dataclass
class PlanDiff:
    version_a: str
    version_b: str
    changes: List[Dict[str, Any]] = field(default_factory=list)
    requires_reapproval: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_a": self.version_a,
            "version_b": self.version_b,
            "changes": self.changes,
            "requires_reapproval": self.requires_reapproval,
        }


@dataclass
class PlanVersion:
    version_id: str
    project_id: str
    parent_version_id: Optional[str]
    revision: int
    created_at: str
    created_by: str
    reason: str
    planning_mode: PlanningMode
    canonical_payload: Dict[str, Any]
    fingerprint: str
    compile_state: str = "COMPILED"
    approval_state: str = "PENDING"
    approved_fingerprint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "project_id": self.project_id,
            "parent_version_id": self.parent_version_id,
            "revision": self.revision,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "reason": self.reason,
            "planning_mode": self.planning_mode.value if isinstance(self.planning_mode, PlanningMode) else self.planning_mode,
            "canonical_payload": self.canonical_payload,
            "fingerprint": self.fingerprint,
            "compile_state": self.compile_state,
            "approval_state": self.approval_state,
            "approved_fingerprint": self.approved_fingerprint,
        }


@dataclass
class ExecutionPlan:
    execution_plan_id: str
    project_id: str
    plan_version_id: str
    fingerprint: str
    compiled_at: str
    resolved_topology: Dict[str, Any]
    resolved_routing: Dict[str, Any]
    resolved_configuration: Dict[str, Any]
    stage1_plan: Dict[str, Any]
    dag_stages: List[Dict[str, Any]]
    is_immutable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_plan_id": self.execution_plan_id,
            "project_id": self.project_id,
            "plan_version_id": self.plan_version_id,
            "fingerprint": self.fingerprint,
            "compiled_at": self.compiled_at,
            "resolved_topology": self.resolved_topology,
            "resolved_routing": self.resolved_routing,
            "resolved_configuration": self.resolved_configuration,
            "stage1_plan": self.stage1_plan,
            "dag_stages": self.dag_stages,
            "is_immutable": self.is_immutable,
        }


@dataclass
class MigrationPlan:
    plan_id: str
    project_id: str
    title: str
    planning_mode: PlanningMode
    topology: TopologyDefinition
    routing: RoutingDefinition
    selected_scope: Dict[str, Any]
    configuration: Dict[str, Any]
    active_version_id: Optional[str] = None
    status: PlanStatus = PlanStatus.DRAFT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "title": self.title,
            "planning_mode": self.planning_mode.value if isinstance(self.planning_mode, PlanningMode) else self.planning_mode,
            "topology": self.topology.to_dict(),
            "routing": self.routing.to_dict(),
            "selected_scope": self.selected_scope,
            "configuration": self.configuration,
            "active_version_id": self.active_version_id,
            "status": self.status.value if isinstance(self.status, PlanStatus) else self.status,
        }


@dataclass
class MigrationProject:
    project_id: str
    title: str
    description: str
    workspace: str
    owner: str
    environment: str
    priority: str
    migration_strategy: str
    source_instance_ref: Dict[str, Any]
    target_instance_ref: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_draft_id: Optional[str] = None
    active_version_id: Optional[str] = None
    compiled_execution_plan_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "workspace": self.workspace,
            "owner": self.owner,
            "environment": self.environment,
            "priority": self.priority,
            "migration_strategy": self.migration_strategy,
            "source_instance_ref": self.source_instance_ref,
            "target_instance_ref": self.target_instance_ref,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_draft_id": self.current_draft_id,
            "active_version_id": self.active_version_id,
            "compiled_execution_plan_id": self.compiled_execution_plan_id,
        }

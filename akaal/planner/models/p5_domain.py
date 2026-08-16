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
class ColumnMapping:
    source_column: str
    target_column: str
    source_object: str
    target_object: str
    is_ignored: bool = False
    target_default: Optional[str] = None
    is_generated: bool = False
    datatype_override: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BulkMappingRule:
    rule_id: str
    rule_type: str  # "SCHEMA_RENAME", "OBJECT_RENAME", "COLUMN_RENAME", "CASE_CONVERT"
    pattern: str
    replacement: str
    is_regex: bool = False
    priority: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MergeMappingSpec:
    target_object: str
    target_schema: str
    source_objects: List[str] = field(default_factory=list)
    merge_strategy: str = "FOUNDATION_UNION"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SplitMappingSpec:
    source_object: str
    source_schema: str
    target_objects: List[str] = field(default_factory=list)
    split_strategy: str = "FOUNDATION_BY_KEY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompiledMapping:
    schema_map: Dict[str, str] = field(default_factory=dict)
    object_map: Dict[str, str] = field(default_factory=dict)
    column_map: Dict[str, Dict[str, str]] = field(default_factory=dict)
    column_order: Dict[str, List[str]] = field(default_factory=dict)
    ignored_columns: Dict[str, List[str]] = field(default_factory=dict)
    target_defaults: Dict[str, Dict[str, str]] = field(default_factory=dict)
    generated_columns: Dict[str, List[str]] = field(default_factory=dict)
    fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoutingDefinition:
    schema_routes: List[SchemaRoute] = field(default_factory=list)
    object_routes: List[ObjectRoute] = field(default_factory=list)
    column_mappings: List[ColumnMapping] = field(default_factory=list)
    bulk_rules: List[BulkMappingRule] = field(default_factory=list)
    merge_foundation: List[MergeMappingSpec] = field(default_factory=list)
    split_foundation: List[SplitMappingSpec] = field(default_factory=list)
    allow_many_to_one: bool = True
    allow_one_to_many: bool = False
    allow_many_to_many: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_routes": [sr.to_dict() for sr in self.schema_routes],
            "object_routes": [orr.to_dict() for orr in self.object_routes],
            "column_mappings": [cm.to_dict() for cm in self.column_mappings],
            "bulk_rules": [br.to_dict() for br in self.bulk_rules],
            "merge_foundation": [mf.to_dict() for mf in self.merge_foundation],
            "split_foundation": [sf.to_dict() for sf in self.split_foundation],
            "allow_many_to_one": self.allow_many_to_one,
            "allow_one_to_many": self.allow_one_to_many,
            "allow_many_to_many": self.allow_many_to_many,
        }


@dataclass
class MappingTemplate:
    template_id: str
    name: str
    version: str
    description: str
    routing: RoutingDefinition
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "routing": self.routing.to_dict(),
            "created_at": self.created_at,
        }


# =====================================================================
# P5.2 DATA SELECTION + FILTERING + PROJECTION DOMAIN MODELS
# =====================================================================

@dataclass
class SelectionRule:
    rule_type: str  # "INCLUDE" or "EXCLUDE"
    target_type: str  # "DATABASE", "SCHEMA", "OBJECT", "COLUMN"
    pattern: str  # Exact name, Glob ("SALES_*"), or Regex ("^APP_.*")
    is_regex: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectionDefinition:
    object_id: str
    selected_columns: List[str] = field(default_factory=list)
    auto_retained_columns: List[str] = field(default_factory=list)  # PK/CDC REQUIRED_BY_AKAAL
    excluded_columns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PredicateDefinition:
    object_id: str
    column: str
    operator: str  # "=", "!=", ">", ">=", "<", "<=", "IN", "NOT IN", "BETWEEN", "IS NULL", "IS NOT NULL", "LIKE"
    value: Any
    pushdown_mode: str = "NATIVE_PUSHDOWN"  # NATIVE_PUSHDOWN, TRANSLATED_PUSHDOWN, AKAAL_SIDE_FILTER, UNSUPPORTED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RangeDefinition:
    object_id: str
    column: str
    start_value: Any
    end_value: Any

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SamplingDefinition:
    method: str = "FIXED_ROWS"  # "FIXED_ROWS" or "PERCENTAGE"
    sample_size: float = 1000.0  # Row count or percentage (e.g. 10.0 for 10%)
    seed: Optional[int] = 42

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SelectionDiagnostic:
    level: str  # "INFO", "WARNING", "BLOCKER"
    code: str
    message: str
    target_object: Optional[str] = None
    suggested_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SelectionEstimate:
    selected_db_count: int = 0
    selected_schema_count: int = 0
    selected_object_count: int = 0
    selected_column_count: int = 0
    estimated_total_rows: int = 0
    estimated_total_bytes: int = 0
    reduction_factor: float = 1.0
    confidence: str = "ESTIMATED"  # EXACT, CATALOG_ESTIMATE, DERIVED_ESTIMATE, UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SelectionPreview:
    object_id: str
    columns: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    total_preview_rows: int = 0
    truncated: bool = False
    sanitized: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SelectionDefinition:
    rules: List[SelectionRule] = field(default_factory=list)
    projections: List[ProjectionDefinition] = field(default_factory=list)
    predicates: List[PredicateDefinition] = field(default_factory=list)
    ranges: List[RangeDefinition] = field(default_factory=list)
    sampling: Optional[SamplingDefinition] = None
    diagnostics: List[SelectionDiagnostic] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rules": [r.to_dict() for r in self.rules],
            "projections": [p.to_dict() for p in self.projections],
            "predicates": [pr.to_dict() for pr in self.predicates],
            "ranges": [rg.to_dict() for rg in self.ranges],
            "sampling": self.sampling.to_dict() if self.sampling else None,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SelectionDefinition":
        if not isinstance(data, dict):
            return cls()
        rules = [SelectionRule(**r) if isinstance(r, dict) else r for r in data.get("rules", [])]
        projections = [ProjectionDefinition(**p) if isinstance(p, dict) else p for p in data.get("projections", [])]
        predicates = [PredicateDefinition(**pr) if isinstance(pr, dict) else pr for pr in data.get("predicates", [])]
        ranges = [RangeDefinition(**rg) if isinstance(rg, dict) else rg for rg in data.get("ranges", [])]
        samp_data = data.get("sampling")
        sampling = SamplingDefinition(**samp_data) if isinstance(samp_data, dict) else None
        diagnostics = [SelectionDiagnostic(**d) if isinstance(d, dict) else d for d in data.get("diagnostics", [])]
        return cls(
            rules=rules,
            projections=projections,
            predicates=predicates,
            ranges=ranges,
            sampling=sampling,
            diagnostics=diagnostics,
        )


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

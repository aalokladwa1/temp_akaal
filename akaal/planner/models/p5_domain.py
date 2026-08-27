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
        rules = []
        for r in data.get("rules", []):
            if isinstance(r, dict):
                if "rule_type" in r and "target_type" in r and "pattern" in r:
                    rules.append(SelectionRule(**r))
                elif "object_name" in r:
                    rules.append(SelectionRule(
                        rule_type="INCLUDE" if r.get("include", True) else "EXCLUDE",
                        target_type="OBJECT",
                        pattern=r["object_name"],
                        is_regex=r.get("is_regex", False),
                    ))
                else:
                    rules.append(SelectionRule(**r))
            else:
                rules.append(r)

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


# =====================================================================
# CANONICAL FIRST-CLASS EXECUTION MODES (M1 - M8)
# =====================================================================

class ExecutionMode(str, Enum):
    """
    Canonical First-Class AKAAL Execution Modes (M1 - M8).
    Frozen production workflow definition.
    """
    M1_BULK_MIGRATION         = "M1"  # M1 — Bulk Migration
    M2_BULK_CDC               = "M2"  # M2 — Bulk + CDC Catchup
    M3_CDC_CONTINUOUS         = "M3"  # M3 — CDC / Continuous Replication
    M4_INCREMENTAL_QUERY      = "M4"  # M4 — Incremental Query / Polling
    M5_STATE_SYNCHRONIZATION  = "M5"  # M5 — State-Based Synchronization
    M6_SCHEMA_ONLY            = "M6"  # M6 — Schema Only
    M7_DATA_ONLY              = "M7"  # M7 — Data Only
    M8_VALIDATION_ONLY        = "M8"  # M8 — Validation / Reconciliation Only

    @classmethod
    def from_string(cls, mode_val: Any) -> "ExecutionMode":
        """Resolves raw string, enum, or canonical alias into canonical ExecutionMode. Fails closed with ValueError."""
        if isinstance(mode_val, cls):
            return mode_val
        if mode_val is None or not str(mode_val).strip():
            raise ValueError("ExecutionMode cannot be empty or None.")

        raw_str = str(mode_val).strip()
        val_str = raw_str.lower().replace("-", "_")

        alias_map = {
            "m1": cls.M1_BULK_MIGRATION,
            "bulk": cls.M1_BULK_MIGRATION,
            "bulk_only": cls.M1_BULK_MIGRATION,
            "bulk_migration": cls.M1_BULK_MIGRATION,
            "initial_load_only": cls.M1_BULK_MIGRATION,
            "full_migration": cls.M1_BULK_MIGRATION,
            "m2": cls.M2_BULK_CDC,
            "bulk_cdc": cls.M2_BULK_CDC,
            "bulk_and_cdc": cls.M2_BULK_CDC,
            "full_with_cdc": cls.M2_BULK_CDC,
            "m3": cls.M3_CDC_CONTINUOUS,
            "cdc": cls.M3_CDC_CONTINUOUS,
            "cdc_only": cls.M3_CDC_CONTINUOUS,
            "continuous_replication": cls.M3_CDC_CONTINUOUS,
            "cdc_continuous": cls.M3_CDC_CONTINUOUS,
            "m4": cls.M4_INCREMENTAL_QUERY,
            "incremental": cls.M4_INCREMENTAL_QUERY,
            "polling": cls.M4_INCREMENTAL_QUERY,
            "polling_watermark": cls.M4_INCREMENTAL_QUERY,
            "incremental_query": cls.M4_INCREMENTAL_QUERY,
            "incremental_polling": cls.M4_INCREMENTAL_QUERY,
            "m5": cls.M5_STATE_SYNCHRONIZATION,
            "state_sync": cls.M5_STATE_SYNCHRONIZATION,
            "state_based_sync": cls.M5_STATE_SYNCHRONIZATION,
            "state_synchronization": cls.M5_STATE_SYNCHRONIZATION,
            "m6": cls.M6_SCHEMA_ONLY,
            "schema_only": cls.M6_SCHEMA_ONLY,
            "schema": cls.M6_SCHEMA_ONLY,
            "ddl_only": cls.M6_SCHEMA_ONLY,
            "m7": cls.M7_DATA_ONLY,
            "data_only": cls.M7_DATA_ONLY,
            "data": cls.M7_DATA_ONLY,
            "rows_only": cls.M7_DATA_ONLY,
            "m8": cls.M8_VALIDATION_ONLY,
            "validation_only": cls.M8_VALIDATION_ONLY,
            "reconciliation_only": cls.M8_VALIDATION_ONLY,
            "compare_without_migrate": cls.M8_VALIDATION_ONLY,
            "selected_object_validation": cls.M8_VALIDATION_ONLY,
            "revalidation": cls.M8_VALIDATION_ONLY,
            "validation": cls.M8_VALIDATION_ONLY,
            "reconciliation": cls.M8_VALIDATION_ONLY,
        }
        if val_str in alias_map:
            return alias_map[val_str]

        upper_val = raw_str.upper()
        for item in cls:
            if item.value == upper_val or item.name == upper_val:
                return item

        raise ValueError(f"Unknown or unsupported execution mode: '{mode_val}'.")

    def get_spec(self) -> "ExecutionModeSpec":
        """Returns canonical capability specification for this execution mode."""
        specs = {
            ExecutionMode.M1_BULK_MIGRATION: ExecutionModeSpec(
                mode=ExecutionMode.M1_BULK_MIGRATION,
                name="M1 — Bulk Migration",
                description="One-time bulk migration with full deduplication, quality rules, and collision policies.",
                processes_rows=True,
                performs_schema=True,
                allows_target_mutation=True,
                allows_dedup_mutation=True,
                allows_data_quality_rules=True,
                uses_cdc=False,
                uses_incremental_polling=False,
                uses_state_comparison=False,
                validation_only=False,
                permits_repair_eligibility_analysis=True,
                permits_repair_execution=True,
                permits_custom_sql_hooks=True,
            ),
            ExecutionMode.M2_BULK_CDC: ExecutionModeSpec(
                mode=ExecutionMode.M2_BULK_CDC,
                name="M2 — Bulk + CDC Catchup",
                description="Bulk snapshot followed by CDC continuous catchup and cutover.",
                processes_rows=True,
                performs_schema=True,
                allows_target_mutation=True,
                allows_dedup_mutation=True,
                allows_data_quality_rules=True,
                uses_cdc=True,
                uses_incremental_polling=False,
                uses_state_comparison=False,
                validation_only=False,
                permits_repair_eligibility_analysis=True,
                permits_repair_execution=True,
                permits_custom_sql_hooks=True,
            ),
            ExecutionMode.M3_CDC_CONTINUOUS: ExecutionModeSpec(
                mode=ExecutionMode.M3_CDC_CONTINUOUS,
                name="M3 — CDC / Continuous Replication",
                description="Continuous replication streaming CDC events without initial bulk snapshot.",
                processes_rows=True,
                performs_schema=False,
                allows_target_mutation=True,
                allows_dedup_mutation=True,
                allows_data_quality_rules=True,
                uses_cdc=True,
                uses_incremental_polling=False,
                uses_state_comparison=False,
                validation_only=False,
                permits_repair_eligibility_analysis=False,
                permits_repair_execution=False,
                permits_custom_sql_hooks=True,
            ),
            ExecutionMode.M4_INCREMENTAL_QUERY: ExecutionModeSpec(
                mode=ExecutionMode.M4_INCREMENTAL_QUERY,
                name="M4 — Incremental Query / Polling",
                description="Incremental polling using high-watermark columns or timestamp query filters.",
                processes_rows=True,
                performs_schema=False,
                allows_target_mutation=True,
                allows_dedup_mutation=True,
                allows_data_quality_rules=True,
                uses_cdc=False,
                uses_incremental_polling=True,
                uses_state_comparison=False,
                validation_only=False,
                permits_repair_eligibility_analysis=False,
                permits_repair_execution=False,
                permits_custom_sql_hooks=True,
            ),
            ExecutionMode.M5_STATE_SYNCHRONIZATION: ExecutionModeSpec(
                mode=ExecutionMode.M5_STATE_SYNCHRONIZATION,
                name="M5 — State-Based Synchronization",
                description="State comparison and differential reconciliation between source and target.",
                processes_rows=True,
                performs_schema=False,
                allows_target_mutation=True,
                allows_dedup_mutation=True,
                allows_data_quality_rules=True,
                uses_cdc=False,
                uses_incremental_polling=False,
                uses_state_comparison=True,
                validation_only=False,
                permits_repair_eligibility_analysis=True,
                permits_repair_execution=True,
                permits_custom_sql_hooks=True,
            ),
            ExecutionMode.M6_SCHEMA_ONLY: ExecutionModeSpec(
                mode=ExecutionMode.M6_SCHEMA_ONLY,
                name="M6 — Schema Only",
                description="DDL metadata extraction and schema deployment only; no row data processing.",
                processes_rows=False,
                performs_schema=True,
                allows_target_mutation=False,
                allows_dedup_mutation=False,
                allows_data_quality_rules=False,
                uses_cdc=False,
                uses_incremental_polling=False,
                uses_state_comparison=False,
                validation_only=False,
                permits_repair_eligibility_analysis=False,
                permits_repair_execution=False,
                permits_custom_sql_hooks=True,
            ),
            ExecutionMode.M7_DATA_ONLY: ExecutionModeSpec(
                mode=ExecutionMode.M7_DATA_ONLY,
                name="M7 — Data Only",
                description="Data load into pre-existing target schema; no schema creation.",
                processes_rows=True,
                performs_schema=False,
                allows_target_mutation=True,
                allows_dedup_mutation=True,
                allows_data_quality_rules=True,
                uses_cdc=False,
                uses_incremental_polling=False,
                uses_state_comparison=False,
                validation_only=False,
                permits_repair_eligibility_analysis=False,
                permits_repair_execution=False,
                permits_custom_sql_hooks=True,
            ),
            ExecutionMode.M8_VALIDATION_ONLY: ExecutionModeSpec(
                mode=ExecutionMode.M8_VALIDATION_ONLY,
                name="M8 — Validation / Reconciliation Only",
                description="Passive verification and reconciliation without mutating target tables.",
                processes_rows=True,
                performs_schema=False,
                allows_target_mutation=False,
                allows_dedup_mutation=False,
                allows_data_quality_rules=True,
                uses_cdc=False,
                uses_incremental_polling=False,
                uses_state_comparison=True,
                validation_only=True,
                permits_repair_eligibility_analysis=True,
                permits_repair_execution=False,
                permits_custom_sql_hooks=True,
            ),
        }
        return specs[self]


@dataclass(frozen=True)
class ExecutionModeSpec:
    mode: ExecutionMode
    name: str
    description: str
    processes_rows: bool
    performs_schema: bool
    allows_target_mutation: bool
    allows_dedup_mutation: bool
    allows_data_quality_rules: bool
    uses_cdc: bool
    uses_incremental_polling: bool
    uses_state_comparison: bool
    validation_only: bool
    permits_repair_eligibility_analysis: bool = False
    permits_repair_execution: bool = False
    permits_custom_sql_hooks: bool = True

    @property
    def reads_source_data(self) -> bool:
        return self.processes_rows or self.performs_schema or self.uses_state_comparison

    @property
    def reads_target_data(self) -> bool:
        return self.mode in (
            ExecutionMode.M2_BULK_CDC,
            ExecutionMode.M5_STATE_SYNCHRONIZATION,
            ExecutionMode.M8_VALIDATION_ONLY,
        )

    @property
    def mutates_source(self) -> bool:
        return False

    @property
    def mutates_target(self) -> bool:
        return self.allows_target_mutation

    @property
    def performs_schema_work(self) -> bool:
        return self.performs_schema

    @property
    def performs_data_movement(self) -> bool:
        return self.processes_rows and self.allows_target_mutation

    @property
    def performs_bulk_transport(self) -> bool:
        return self.mode in (ExecutionMode.M1_BULK_MIGRATION, ExecutionMode.M2_BULK_CDC)

    @property
    def requires_cdc(self) -> bool:
        return self.mode in (ExecutionMode.M2_BULK_CDC, ExecutionMode.M3_CDC_CONTINUOUS)

    @property
    def permits_cdc(self) -> bool:
        return self.mode in (ExecutionMode.M2_BULK_CDC, ExecutionMode.M3_CDC_CONTINUOUS)

    @property
    def performs_validation(self) -> bool:
        return True

    @property
    def permits_reconciliation(self) -> bool:
        return self.uses_state_comparison or self.validation_only

    @property
    def permits_governed_repair(self) -> bool:
        """
        Governed repair execution permission.
        M8 ordinary operation may NOT execute repair. M8 may evaluate repair eligibility.
        """
        return self.permits_repair_execution

    @property
    def permits_deduplication(self) -> bool:
        return self.allows_dedup_mutation

    @property
    def requires_target_write_authority(self) -> bool:
        return self.allows_target_mutation or self.performs_schema

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "name": self.name,
            "description": self.description,
            "processes_rows": self.processes_rows,
            "performs_schema": self.performs_schema,
            "allows_target_mutation": self.allows_target_mutation,
            "allows_dedup_mutation": self.allows_dedup_mutation,
            "allows_data_quality_rules": self.allows_data_quality_rules,
            "uses_cdc": self.uses_cdc,
            "uses_incremental_polling": self.uses_incremental_polling,
            "uses_state_comparison": self.uses_state_comparison,
            "validation_only": self.validation_only,
            "permits_repair_eligibility_analysis": self.permits_repair_eligibility_analysis,
            "permits_repair_execution": self.permits_repair_execution,
            "permits_governed_repair": self.permits_governed_repair,
            "permits_custom_sql_hooks": self.permits_custom_sql_hooks,
            "reads_source_data": self.reads_source_data,
            "reads_target_data": self.reads_target_data,
            "mutates_source": self.mutates_source,
            "mutates_target": self.mutates_target,
            "performs_schema_work": self.performs_schema_work,
            "performs_data_movement": self.performs_data_movement,
            "performs_bulk_transport": self.performs_bulk_transport,
            "requires_cdc": self.requires_cdc,
            "permits_cdc": self.permits_cdc,
            "performs_validation": self.performs_validation,
            "permits_reconciliation": self.permits_reconciliation,
            "permits_deduplication": self.permits_deduplication,
            "requires_target_write_authority": self.requires_target_write_authority,
        }


# =====================================================================
# P5.8 PREFLIGHT, DRY-RUN & REPAIR ELIGIBILITY CANONICAL DTOs
# =====================================================================

@dataclass(frozen=True)
class PreflightDiagnostic:
    code: str
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    target_object: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    remediation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "target_object": self.target_object,
            "details": dict(self.details),
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class PreflightResult:
    passed: bool
    checks_evaluated: int
    checks_passed: int
    checks_failed: int
    diagnostics: List[PreflightDiagnostic] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "checks_evaluated": self.checks_evaluated,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class DryRunResult:
    plan_id: str
    mode: str
    compiled_nodes_count: int
    compiled_edges_count: int
    dag_preview: List[Dict[str, Any]] = field(default_factory=list)
    connector_decisions: Dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""
    writes_committed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "mode": self.mode,
            "compiled_nodes_count": self.compiled_nodes_count,
            "compiled_edges_count": self.compiled_edges_count,
            "dag_preview": list(self.dag_preview),
            "connector_decisions": dict(self.connector_decisions),
            "fingerprint": self.fingerprint,
            "writes_committed": self.writes_committed,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RepairEligibilityResult:
    table_name: str
    discrepancies_found: int
    eligible_for_repair: bool
    repair_strategy: str
    repair_execution_blocked: bool = True
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "discrepancies_found": self.discrepancies_found,
            "eligible_for_repair": self.eligible_for_repair,
            "repair_strategy": self.repair_strategy,
            "repair_execution_blocked": self.repair_execution_blocked,
            "reason": self.reason,
            "details": dict(self.details),
        }


# =====================================================================
# P5.6 DEDUPLICATION + DATA QUALITY + CONFLICT POLICIES DOMAIN MODELS
# =====================================================================

class SurvivorStrategy(str, Enum):
    FIRST = "FIRST"                        # Explicit deterministic order first
    LAST = "LAST"                          # Explicit deterministic order last
    MIN_FIELD = "MIN_FIELD"                # Minimum value in specified field
    MAX_FIELD = "MAX_FIELD"                # Maximum value in specified field
    NEWEST = "NEWEST"                      # Newest timestamp in specified field
    OLDEST = "OLDEST"                      # Oldest timestamp in specified field
    PRIORITY = "PRIORITY"                  # Priority according to configured mapping
    REJECT_GROUP = "REJECT_GROUP"          # Reject all records in duplicate group
    QUARANTINE_GROUP = "QUARANTINE_GROUP"  # Quarantine all records in duplicate group
    FAIL_ON_DUPLICATE = "FAIL_ON_DUPLICATE" # Fail execution immediately on duplicate


class DuplicateDisposition(str, Enum):
    DISCARD = "DISCARD"
    REJECT = "REJECT"
    QUARANTINE = "QUARANTINE"
    FAIL = "FAIL"


class CollisionPolicy(str, Enum):
    FAIL = "FAIL"
    REJECT = "REJECT"
    QUARANTINE = "QUARANTINE"
    SKIP = "SKIP"                          # DO NOTHING / INSERT IGNORE
    INSERT = "INSERT"                      # Standard INSERT
    UPDATE = "UPDATE"                      # UPDATE target
    UPSERT = "UPSERT"                      # Dialect-aware UPSERT / MERGE


class QualityRuleType(str, Enum):
    NOT_NULL = "NOT_NULL"
    VALUE_RANGE = "VALUE_RANGE"
    REGEX_MATCH = "REGEX_MATCH"
    ENUM_VALUES = "ENUM_VALUES"
    MAX_LENGTH = "MAX_LENGTH"
    NUMERIC_OVERFLOW = "NUMERIC_OVERFLOW"
    CUSTOM_PREDICATE = "CUSTOM_PREDICATE"


class QualityViolationPolicy(str, Enum):
    FAIL_JOB = "FAIL_JOB"
    REJECT_RECORD = "REJECT_RECORD"
    QUARANTINE_RECORD = "QUARANTINE_RECORD"
    USE_DEFAULT = "USE_DEFAULT"
    USE_NULL = "USE_NULL"
    EXPLICIT_TRUNCATE = "EXPLICIT_TRUNCATE"
    WARN_ONLY = "WARN_ONLY"


class QualityGateConsequence(str, Enum):
    WARN = "WARN"
    BLOCK_CUTOVER = "BLOCK_CUTOVER"
    FAIL_JOB = "FAIL_JOB"


@dataclass
class DeduplicationRule:
    object_name: str
    key_columns: List[str]
    enabled: bool = True
    survivor_strategy: SurvivorStrategy = SurvivorStrategy.FIRST
    order_by_columns: List[str] = field(default_factory=list)  # e.g. ["updated_at DESC", "id ASC"]
    priority_field: Optional[str] = None
    priority_order: List[Any] = field(default_factory=list)
    disposition: DuplicateDisposition = DuplicateDisposition.DISCARD
    collision_policy: CollisionPolicy = CollisionPolicy.FAIL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_name": self.object_name,
            "key_columns": self.key_columns,
            "enabled": self.enabled,
            "survivor_strategy": self.survivor_strategy.value if isinstance(self.survivor_strategy, Enum) else self.survivor_strategy,
            "order_by_columns": self.order_by_columns,
            "priority_field": self.priority_field,
            "priority_order": self.priority_order,
            "disposition": self.disposition.value if isinstance(self.disposition, Enum) else self.disposition,
            "collision_policy": self.collision_policy.value if isinstance(self.collision_policy, Enum) else self.collision_policy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeduplicationRule":
        if not isinstance(data, dict):
            raise ValueError("DeduplicationRule data must be a dictionary.")
        strat = data.get("survivor_strategy", SurvivorStrategy.FIRST)
        if isinstance(strat, str):
            strat = SurvivorStrategy(strat.upper())
        disp = data.get("disposition", DuplicateDisposition.DISCARD)
        if isinstance(disp, str):
            disp = DuplicateDisposition(disp.upper())
        coll = data.get("collision_policy", CollisionPolicy.FAIL)
        if isinstance(coll, str):
            coll = CollisionPolicy(coll.upper())
        return cls(
            object_name=data["object_name"],
            key_columns=list(data.get("key_columns", [])),
            enabled=data.get("enabled", True),
            survivor_strategy=strat,
            order_by_columns=list(data.get("order_by_columns", [])),
            priority_field=data.get("priority_field"),
            priority_order=list(data.get("priority_order", [])),
            disposition=disp,
            collision_policy=coll,
        )


@dataclass
class DeduplicationDefinition:
    enabled: bool = True
    global_collision_policy: CollisionPolicy = CollisionPolicy.FAIL
    rules: List[DeduplicationRule] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "global_collision_policy": self.global_collision_policy.value if isinstance(self.global_collision_policy, Enum) else self.global_collision_policy,
            "rules": [r.to_dict() for r in self.rules],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeduplicationDefinition":
        if not isinstance(data, dict):
            return cls()
        coll = data.get("global_collision_policy", CollisionPolicy.FAIL)
        if isinstance(coll, str):
            coll = CollisionPolicy(coll.upper())
        rules = [
            DeduplicationRule.from_dict(r) if isinstance(r, dict) else r
            for r in data.get("rules", [])
        ]
        return cls(
            enabled=data.get("enabled", True),
            global_collision_policy=coll,
            rules=rules,
        )


@dataclass
class DataQualityRule:
    rule_id: str
    object_name: str
    column_name: str
    rule_type: QualityRuleType
    violation_policy: QualityViolationPolicy = QualityViolationPolicy.QUARANTINE_RECORD
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    regex_pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    max_length: Optional[int] = None
    allow_truncation: bool = False
    target_datatype: Optional[str] = None
    default_value: Optional[Any] = None
    predicate_expression: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "object_name": self.object_name,
            "column_name": self.column_name,
            "rule_type": self.rule_type.value if isinstance(self.rule_type, Enum) else self.rule_type,
            "violation_policy": self.violation_policy.value if isinstance(self.violation_policy, Enum) else self.violation_policy,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "regex_pattern": self.regex_pattern,
            "allowed_values": self.allowed_values,
            "max_length": self.max_length,
            "allow_truncation": self.allow_truncation,
            "target_datatype": self.target_datatype,
            "default_value": self.default_value,
            "predicate_expression": self.predicate_expression,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataQualityRule":
        if not isinstance(data, dict):
            raise ValueError("DataQualityRule data must be a dictionary.")
        rtype = data.get("rule_type", QualityRuleType.NOT_NULL)
        if isinstance(rtype, str):
            rtype = QualityRuleType(rtype.upper())
        vpol = data.get("violation_policy", QualityViolationPolicy.QUARANTINE_RECORD)
        if isinstance(vpol, str):
            vpol = QualityViolationPolicy(vpol.upper())
        return cls(
            rule_id=data.get("rule_id", str(uuid.uuid4())),
            object_name=data["object_name"],
            column_name=data["column_name"],
            rule_type=rtype,
            violation_policy=vpol,
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            regex_pattern=data.get("regex_pattern"),
            allowed_values=data.get("allowed_values"),
            max_length=data.get("max_length"),
            allow_truncation=data.get("allow_truncation", False),
            target_datatype=data.get("target_datatype"),
            default_value=data.get("default_value"),
            predicate_expression=data.get("predicate_expression"),
        )


@dataclass
class QualityThreshold:
    max_duplicate_count: Optional[int] = None
    max_duplicate_percentage: Optional[float] = None
    max_invalid_count: Optional[int] = None
    max_invalid_percentage: Optional[float] = None
    max_reject_count: Optional[int] = None
    max_quarantine_count: Optional[int] = None
    max_total_violations: Optional[int] = None
    consequence: QualityGateConsequence = QualityGateConsequence.FAIL_JOB

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_duplicate_count": self.max_duplicate_count,
            "max_duplicate_percentage": self.max_duplicate_percentage,
            "max_invalid_count": self.max_invalid_count,
            "max_invalid_percentage": self.max_invalid_percentage,
            "max_reject_count": self.max_reject_count,
            "max_quarantine_count": self.max_quarantine_count,
            "max_total_violations": self.max_total_violations,
            "consequence": self.consequence.value if isinstance(self.consequence, Enum) else self.consequence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityThreshold":
        if not isinstance(data, dict):
            return cls()
        conseq = data.get("consequence", QualityGateConsequence.FAIL_JOB)
        if isinstance(conseq, str):
            conseq = QualityGateConsequence(conseq.upper())
        return cls(
            max_duplicate_count=data.get("max_duplicate_count"),
            max_duplicate_percentage=data.get("max_duplicate_percentage"),
            max_invalid_count=data.get("max_invalid_count"),
            max_invalid_percentage=data.get("max_invalid_percentage"),
            max_reject_count=data.get("max_reject_count"),
            max_quarantine_count=data.get("max_quarantine_count"),
            max_total_violations=data.get("max_total_violations"),
            consequence=conseq,
        )


@dataclass
class DataQualityDefinition:
    rules: List[DataQualityRule] = field(default_factory=list)
    global_threshold: Optional[QualityThreshold] = None
    object_thresholds: Dict[str, QualityThreshold] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rules": [r.to_dict() for r in self.rules],
            "global_threshold": self.global_threshold.to_dict() if self.global_threshold else None,
            "object_thresholds": {k: v.to_dict() for k, v in self.object_thresholds.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataQualityDefinition":
        if not isinstance(data, dict):
            return cls()
        rules = [
            DataQualityRule.from_dict(r) if isinstance(r, dict) else r
            for r in data.get("rules", [])
        ]
        g_thresh = (
            QualityThreshold.from_dict(data["global_threshold"])
            if isinstance(data.get("global_threshold"), dict)
            else None
        )
        o_thresh = {}
        for k, v in data.get("object_thresholds", {}).items():
            if isinstance(v, dict):
                o_thresh[k] = QualityThreshold.from_dict(v)
            elif isinstance(v, QualityThreshold):
                o_thresh[k] = v
        return cls(
            rules=rules,
            global_threshold=g_thresh,
            object_thresholds=o_thresh,
        )


@dataclass
class QualityGateResult:
    passed: bool
    consequence: QualityGateConsequence
    total_violations: int
    duplicate_count: int
    invalid_count: int
    reject_count: int
    quarantine_count: int
    violation_messages: List[str] = field(default_factory=list)
    cutover_blocked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "consequence": self.consequence.value if isinstance(self.consequence, Enum) else self.consequence,
            "total_violations": self.total_violations,
            "duplicate_count": self.duplicate_count,
            "invalid_count": self.invalid_count,
            "reject_count": self.reject_count,
            "quarantine_count": self.quarantine_count,
            "violation_messages": self.violation_messages,
            "cutover_blocked": self.cutover_blocked,
        }


@dataclass
class ConflictPolicyConfiguration:
    default_policy: str = "SOURCE_A_WINS"  # Links to P3 CDCConflictResolutionPolicy
    object_overrides: Dict[str, str] = field(default_factory=dict)
    designated_primary_node: Optional[str] = None
    max_unresolved_conflicts: int = 0
    fail_on_unresolved_conflict: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConflictPolicyConfiguration":
        if not isinstance(data, dict):
            return cls()
        return cls(
            default_policy=str(data.get("default_policy", "SOURCE_A_WINS")).upper(),
            object_overrides=dict(data.get("object_overrides", {})),
            designated_primary_node=data.get("designated_primary_node"),
            max_unresolved_conflicts=int(data.get("max_unresolved_conflicts", 0)),
            fail_on_unresolved_conflict=bool(data.get("fail_on_unresolved_conflict", True)),
        )


# ===========================================================================
# P5.7: Custom SQL + Hooks + Governed Extensibility Domain Models
# ===========================================================================

class HookStage(str, Enum):
    """Execution lifecycle stages for custom SQL hooks."""
    PRE_MIGRATION = "PRE_MIGRATION"
    SESSION_INITIALIZATION = "SESSION_INITIALIZATION"
    TARGET_PREPARATION = "TARGET_PREPARATION"
    PRE_OBJECT = "PRE_OBJECT"
    POST_OBJECT = "POST_OBJECT"
    TARGET_FINALIZATION = "TARGET_FINALIZATION"
    POST_MIGRATION = "POST_MIGRATION"


class HookSide(str, Enum):
    """Database side on which hook executes."""
    SOURCE = "SOURCE"
    TARGET = "TARGET"


class HookTransactionPolicy(str, Enum):
    """Transaction semantics for hook execution."""
    AUTO_COMMIT = "AUTO_COMMIT"
    PARTICIPATE_EXISTING = "PARTICIPATE_EXISTING"
    ISOLATED_TRANSACTION = "ISOLATED_TRANSACTION"
    NO_TRANSACTION = "NO_TRANSACTION"


class HookIdempotencyClassification(str, Enum):
    """Idempotency / replay protection classification."""
    IDEMPOTENT = "IDEMPOTENT"
    NON_IDEMPOTENT = "NON_IDEMPOTENT"
    REPLAY_PROTECTED = "REPLAY_PROTECTED"
    UNKNOWN = "UNKNOWN"


class HookFailurePolicy(str, Enum):
    """Action taken when a hook fails."""
    FAIL_FAST = "FAIL_FAST"
    CONTINUE_ON_FAILURE = "CONTINUE_ON_FAILURE"
    REQUIRE_OPERATOR = "REQUIRE_OPERATOR"
    ROLLBACK_AND_ABORT = "ROLLBACK_AND_ABORT"


class HookExecutionState(str, Enum):
    """Durable state tracking for hook execution."""
    NOT_STARTED = "NOT_STARTED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    AMBIGUOUS = "AMBIGUOUS"
    SKIPPED = "SKIPPED"


class SQLSafetyClassification(str, Enum):
    """Static and semantic classification of custom SQL statement risk."""
    SAFE_SELECT = "SAFE_SELECT"
    SAFE_MUTATING = "SAFE_MUTATING"
    DESTRUCTIVE_DML = "DESTRUCTIVE_DML"
    DESTRUCTIVE_DDL = "DESTRUCTIVE_DDL"
    PRIVILEGE_MODIFICATION = "PRIVILEGE_MODIFICATION"
    UNKNOWN_UNCLASSIFIED = "UNKNOWN_UNCLASSIFIED"


@dataclass
class HookDefinition:
    """Canonical specification for a governed custom SQL hook."""
    hook_id: str
    name: str
    stage: HookStage
    sql_statement: str
    description: str = ""
    side: HookSide = HookSide.TARGET
    scope_object: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    dependencies: List[str] = field(default_factory=list)
    order: int = 100
    timeout_ms: int = 30000
    transaction_policy: HookTransactionPolicy = HookTransactionPolicy.AUTO_COMMIT
    idempotency: HookIdempotencyClassification = HookIdempotencyClassification.NON_IDEMPOTENT
    failure_policy: HookFailurePolicy = HookFailurePolicy.FAIL_FAST
    requires_approval: bool = False
    enabled: bool = True
    allow_rules: Optional[List[str]] = None
    deny_rules: Optional[List[str]] = None
    safety_classification: Optional[SQLSafetyClassification] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hook_id": self.hook_id,
            "name": self.name,
            "description": self.description,
            "stage": self.stage.value if isinstance(self.stage, Enum) else str(self.stage),
            "side": self.side.value if isinstance(self.side, Enum) else str(self.side),
            "scope_object": self.scope_object,
            "sql_statement": self.sql_statement,
            "parameters": dict(self.parameters) if self.parameters else None,
            "dependencies": list(self.dependencies),
            "order": self.order,
            "timeout_ms": self.timeout_ms,
            "transaction_policy": (
                self.transaction_policy.value
                if isinstance(self.transaction_policy, Enum)
                else str(self.transaction_policy)
            ),
            "idempotency": (
                self.idempotency.value
                if isinstance(self.idempotency, Enum)
                else str(self.idempotency)
            ),
            "failure_policy": (
                self.failure_policy.value
                if isinstance(self.failure_policy, Enum)
                else str(self.failure_policy)
            ),
            "requires_approval": self.requires_approval,
            "enabled": self.enabled,
            "allow_rules": list(self.allow_rules) if self.allow_rules is not None else None,
            "deny_rules": list(self.deny_rules) if self.deny_rules is not None else None,
            "safety_classification": (
                self.safety_classification.value
                if isinstance(self.safety_classification, Enum)
                else (str(self.safety_classification) if self.safety_classification else None)
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HookDefinition":
        if not isinstance(data, dict):
            raise ValueError("HookDefinition data must be a dictionary.")

        def _enum_val(enum_cls, val, default):
            if val is None:
                return default
            if isinstance(val, enum_cls):
                return val
            try:
                return enum_cls(str(val).upper())
            except Exception:
                return default

        stage = _enum_val(HookStage, data.get("stage"), HookStage.PRE_MIGRATION)
        side = _enum_val(HookSide, data.get("side"), HookSide.TARGET)
        tx_pol = _enum_val(HookTransactionPolicy, data.get("transaction_policy"), HookTransactionPolicy.AUTO_COMMIT)
        idem = _enum_val(HookIdempotencyClassification, data.get("idempotency"), HookIdempotencyClassification.NON_IDEMPOTENT)
        fail_pol = _enum_val(HookFailurePolicy, data.get("failure_policy"), HookFailurePolicy.FAIL_FAST)
        safety = _enum_val(SQLSafetyClassification, data.get("safety_classification"), None) if data.get("safety_classification") else None

        return cls(
            hook_id=str(data["hook_id"]).strip(),
            name=str(data.get("name", data["hook_id"])),
            stage=stage,
            sql_statement=str(data.get("sql_statement", "")),
            description=str(data.get("description", "")),
            side=side,
            scope_object=data.get("scope_object"),
            parameters=dict(data.get("parameters", {})) if data.get("parameters") else None,
            dependencies=list(data.get("dependencies", [])),
            order=int(data.get("order", 100)),
            timeout_ms=int(data.get("timeout_ms", 30000)),
            transaction_policy=tx_pol,
            idempotency=idem,
            failure_policy=fail_pol,
            requires_approval=bool(data.get("requires_approval", False)),
            enabled=bool(data.get("enabled", True)),
            allow_rules=list(data.get("allow_rules", [])) if data.get("allow_rules") is not None else None,
            deny_rules=list(data.get("deny_rules", [])) if data.get("deny_rules") is not None else None,
            safety_classification=safety,
        )


@dataclass
class HooksConfiguration:
    """Global configuration container for custom SQL hooks in a migration."""
    enabled: bool = True
    hooks: List[HookDefinition] = field(default_factory=list)
    global_timeout_ms: int = 60000
    allow_dangerous_sql: bool = False
    require_approval_for_destructive: bool = True
    allow_rules: Optional[List[str]] = None
    deny_rules: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "global_timeout_ms": self.global_timeout_ms,
            "allow_dangerous_sql": self.allow_dangerous_sql,
            "require_approval_for_destructive": self.require_approval_for_destructive,
            "allow_rules": self.allow_rules,
            "deny_rules": self.deny_rules,
            "hooks": [h.to_dict() for h in self.hooks],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HooksConfiguration":
        if not isinstance(data, dict):
            return cls()
        hooks = [
            HookDefinition.from_dict(h) if isinstance(h, dict) else h
            for h in data.get("hooks", [])
        ]
        return cls(
            enabled=bool(data.get("enabled", True)),
            global_timeout_ms=int(data.get("global_timeout_ms", 60000)),
            allow_dangerous_sql=bool(data.get("allow_dangerous_sql", False)),
            require_approval_for_destructive=bool(data.get("require_approval_for_destructive", True)),
            allow_rules=data.get("allow_rules"),
            deny_rules=data.get("deny_rules"),
            hooks=hooks,
        )


@dataclass
class HookExecutionResult:
    """Physical outcome and telemetry for an executed hook."""
    hook_id: str
    stage: HookStage
    state: HookExecutionState
    rows_affected: int = 0
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    sanitized_sql: Optional[str] = None
    is_ambiguous: bool = False
    audit_entry_id: Optional[str] = None
    side: HookSide = HookSide.TARGET

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hook_id": self.hook_id,
            "stage": self.stage.value if isinstance(self.stage, Enum) else str(self.stage),
            "side": self.side.value if isinstance(self.side, Enum) else str(self.side),
            "state": self.state.value if isinstance(self.state, Enum) else str(self.state),
            "rows_affected": self.rows_affected,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "sanitized_sql": self.sanitized_sql,
            "is_ambiguous": self.is_ambiguous,
            "audit_entry_id": self.audit_entry_id,
        }


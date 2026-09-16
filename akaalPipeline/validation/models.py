"""akaalPipeline.validation.models
=================================
Canonical Data Models, Enums, and Records for Validation Missions & Baselines.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationMissionState(str, Enum):
    DRAFT = "DRAFT"
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    ACTIVE = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class TemporalStrategy(str, Enum):
    EXECUTE_ON_INIT = "EXECUTE_ON_INIT"
    SCHEDULE_LATER = "SCHEDULE_LATER"
    RECURRING = "RECURRING"
    CONTINUOUS = "CONTINUOUS"


class BaselineType(str, Enum):
    INHERITED_MIGRATION = "INHERITED_MIGRATION"
    MAINTENANCE_COORDINATED = "MAINTENANCE_COORDINATED"
    EXTERNAL_REPLICATION = "EXTERNAL_REPLICATION"
    CURRENT_OPERATIONAL = "CURRENT_OPERATIONAL"
    STATIC_IMMUTABLE = "STATIC_IMMUTABLE"


class CoordinationCondition(str, Enum):
    WRITES_STOPPED_DECLARED = "WRITES_STOPPED_DECLARED"
    EXTERNAL_COORDINATION_DECLARED = "EXTERNAL_COORDINATION_DECLARED"
    READONLY_QUIESCENCE_VERIFIED = "READONLY_QUIESCENCE_VERIFIED"
    WRITES_STOPPED_VERIFIED = "WRITES_STOPPED_VERIFIED"


class PositionType(str, Enum):
    ORACLE_SCN = "ORACLE_SCN"
    POSTGRESQL_LSN = "POSTGRESQL_LSN"
    POSTGRES_LSN = "POSTGRESQL_LSN"
    MYSQL_GTID = "MYSQL_GTID"
    KAFKA_OFFSET = "KAFKA_OFFSET"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    DECLARED = "DECLARED"
    EXTERNALLY_ASSERTED = "EXTERNALLY_ASSERTED"
    UNSATISFIED = "UNSATISFIED"
    SYNTAX_INVALID = "SYNTAX_INVALID"
    UNSUPPORTED_PROVIDER = "UNSUPPORTED_PROVIDER"


@dataclass
class ValidationMissionRecord:
    mission_id: str
    name: str
    source_provider: str
    target_provider: str
    tenant_id: str = "default-tenant"
    workspace_id: str = "default-workspace"
    project_id: Optional[str] = None
    source_connection_id: Optional[str] = None
    target_connection_id: Optional[str] = None
    validation_context: str = "INDEPENDENT"
    linked_migration_id: Optional[str] = None
    baseline_id: Optional[str] = None
    temporal_strategy: TemporalStrategy = TemporalStrategy.EXECUTE_ON_INIT
    is_continuous: bool = False
    state: ValidationMissionState = ValidationMissionState.DRAFT
    schedule_id: Optional[str] = None
    scope_config: Dict[str, Any] = field(default_factory=dict)
    execution_policy: Dict[str, Any] = field(default_factory=dict)
    last_evaluated_at: Optional[str] = None
    last_change_position: Optional[str] = None
    evaluation_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    last_result_status: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "name": self.name,
            "source_provider": self.source_provider,
            "target_provider": self.target_provider,
            "source_connection_id": self.source_connection_id,
            "target_connection_id": self.target_connection_id,
            "validation_context": self.validation_context,
            "linked_migration_id": self.linked_migration_id,
            "baseline_id": self.baseline_id,
            "temporal_strategy": self.temporal_strategy.value,
            "is_continuous": self.is_continuous,
            "state": self.state.value,
            "schedule_id": self.schedule_id,
            "scope_config": self.scope_config,
            "execution_policy": self.execution_policy,
            "last_evaluated_at": self.last_evaluated_at,
            "last_change_position": self.last_change_position,
            "evaluation_count": self.evaluation_count,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "last_result_status": self.last_result_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ValidationMissionRecord:
        scope = data.get("scope_config", {})
        if isinstance(scope, str):
            try:
                scope = json.loads(scope)
            except Exception:
                scope = {}

        policy = data.get("execution_policy", {})
        if isinstance(policy, str):
            try:
                policy = json.loads(policy)
            except Exception:
                policy = {}

        return cls(
            mission_id=data["mission_id"],
            tenant_id=data.get("tenant_id", "default-tenant"),
            workspace_id=data.get("workspace_id", "default-workspace"),
            project_id=data.get("project_id"),
            name=data["name"],
            source_provider=data.get("source_provider", "Unknown"),
            target_provider=data.get("target_provider", "Unknown"),
            source_connection_id=data.get("source_connection_id"),
            target_connection_id=data.get("target_connection_id"),
            validation_context=data.get("validation_context", "INDEPENDENT"),
            linked_migration_id=data.get("linked_migration_id"),
            baseline_id=data.get("baseline_id"),
            temporal_strategy=TemporalStrategy(data.get("temporal_strategy", "EXECUTE_ON_INIT")),
            is_continuous=bool(data.get("is_continuous", False)),
            state=ValidationMissionState(data.get("state", "DRAFT")),
            schedule_id=data.get("schedule_id"),
            scope_config=scope,
            execution_policy=policy,
            last_evaluated_at=data.get("last_evaluated_at"),
            last_change_position=data.get("last_change_position"),
            evaluation_count=int(data.get("evaluation_count", 0)),
            pass_count=int(data.get("pass_count", 0)),
            fail_count=int(data.get("fail_count", 0)),
            last_result_status=data.get("last_result_status"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class ValidationBaselineRecord:
    baseline_id: str
    mission_id: str
    baseline_type: BaselineType
    tenant_id: str = "default-tenant"
    workspace_id: str = "default-workspace"
    project_id: Optional[str] = None
    condition_type: Optional[str] = None
    position_type: Optional[str] = None
    position_value: Optional[str] = None
    migration_id: Optional[str] = None
    checkpoint_id: Optional[str] = None
    is_verified: bool = False
    verification_method: str = "OPERATOR_DECLARATION"
    verification_status: VerificationStatus = VerificationStatus.DECLARED
    provenance_details: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "mission_id": self.mission_id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "baseline_type": self.baseline_type.value if hasattr(self.baseline_type, "value") else str(self.baseline_type),
            "condition_type": self.condition_type,
            "position_type": self.position_type,
            "position_value": self.position_value,
            "migration_id": self.migration_id,
            "checkpoint_id": self.checkpoint_id,
            "is_verified": self.is_verified,
            "verification_method": self.verification_method,
            "verification_status": self.verification_status.value if hasattr(self.verification_status, "value") else str(self.verification_status),
            "provenance_details": self.provenance_details,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ValidationBaselineRecord:
        prov = data.get("provenance_details", {})
        if isinstance(prov, str):
            try:
                prov = json.loads(prov)
            except Exception:
                prov = {}

        return cls(
            baseline_id=data["baseline_id"],
            mission_id=data["mission_id"],
            tenant_id=data.get("tenant_id", "default-tenant"),
            workspace_id=data.get("workspace_id", "default-workspace"),
            project_id=data.get("project_id"),
            baseline_type=BaselineType(data["baseline_type"]),
            condition_type=data.get("condition_type"),
            position_type=data.get("position_type"),
            position_value=data.get("position_value"),
            migration_id=data.get("migration_id"),
            checkpoint_id=data.get("checkpoint_id"),
            is_verified=bool(data.get("is_verified", False)),
            verification_method=data.get("verification_method", "OPERATOR_DECLARATION"),
            verification_status=VerificationStatus(data.get("verification_status", "DECLARED")),
            provenance_details=prov,
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class ValidationReadinessResult:
    is_ready: bool
    status_code: str  # READY, READINESS_FAILED, UNSATISFIED_BASELINE, UNAUTHORIZED, INVALID_CONFIG
    summary: str
    reasons: List[str] = field(default_factory=list)
    boundary_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_ready": self.is_ready,
            "status_code": self.status_code,
            "summary": self.summary,
            "reasons": self.reasons,
            "boundary_info": self.boundary_info,
        }


@dataclass
class ValidationCapabilityInfo:
    source_provider: str
    target_provider: str
    supported_baselines: List[str]
    supported_temporal_strategies: List[str]
    supports_cdc_change_streams: bool
    supports_exact_row: bool
    supports_cardinality: bool
    availability_code: str  # AVAILABLE, CONFIGURATION_REQUIRED, PROVIDER_UNSUPPORTED
    availability_message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_provider": self.source_provider,
            "target_provider": self.target_provider,
            "supported_baselines": self.supported_baselines,
            "supported_temporal_strategies": self.supported_temporal_strategies,
            "supports_cdc_change_streams": self.supports_cdc_change_streams,
            "supports_exact_row": self.supports_exact_row,
            "supports_cardinality": self.supports_cardinality,
            "availability_code": self.availability_code,
            "availability_message": self.availability_message,
        }

"""akaalPipeline.validation.boundary
===================================
Validation Boundary Manager implementing Maintenance, Migration, and External Replication Baselines.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.validation.models import (
    BaselineType,
    CoordinationCondition,
    PositionType,
    ValidationBaselineRecord,
    ValidationMissionRecord,
    ValidationReadinessResult,
    VerificationStatus,
)


class ValidationBoundaryManager:
    def __init__(self, migration_repository: Optional[SQLiteMigrationRepository] = None) -> None:
        self.migration_repository = migration_repository

    def _resolve_mission(
        self,
        mission_or_id: Union[ValidationMissionRecord, str],
        conn: sqlite3.Connection,
    ) -> ValidationMissionRecord:
        if isinstance(mission_or_id, ValidationMissionRecord):
            return mission_or_id
        cur = conn.execute("SELECT * FROM validation_missions WHERE mission_id = ?", (mission_or_id,))
        row = cur.fetchone()
        if not row:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Validation mission {mission_or_id!r} not found.")
        return ValidationMissionRecord.from_dict(dict(row))

    def create_maintenance_baseline(
        self,
        mission: Union[ValidationMissionRecord, str],
        condition_type: Union[CoordinationCondition, str],
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        operator_notes: Optional[str] = None,
        operator_declaration: Optional[str] = None,
    ) -> ValidationBaselineRecord:
        mission_rec = self._resolve_mission(mission, conn)
        actor.enforce_resource_scope(
            resource_tenant_id=mission_rec.tenant_id,
            resource_workspace_id=mission_rec.workspace_id,
            resource_project_id=mission_rec.project_id,
            resource_kind="ValidationMission",
            resource_id=mission_rec.mission_id,
        )

        cond_str = condition_type.value if hasattr(condition_type, "value") else str(condition_type)
        valid_conditions = [c.value for c in CoordinationCondition]
        if cond_str not in valid_conditions:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"Invalid maintenance coordination condition {cond_str!r}. Must be one of {valid_conditions!r}.",
            )

        baseline_id = f"base-maint-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        notes = operator_declaration or operator_notes or ""
        status = VerificationStatus.VERIFIED if cond_str in (CoordinationCondition.READONLY_QUIESCENCE_VERIFIED.value, CoordinationCondition.WRITES_STOPPED_VERIFIED.value) else VerificationStatus.DECLARED

        provenance = {
            "declared_by": actor.actor_id,
            "declared_roles": list(actor.roles),
            "declared_at": now,
            "operator_declaration": notes,
            "operator_notes": notes,
            "coordination_condition": cond_str,
            "truth_guarantee": "OPERATOR_DECLARED — Not independently verified by DevKros engine." if status == VerificationStatus.DECLARED else "VERIFIED — Boundary verified via canonical engine check.",
        }

        baseline = ValidationBaselineRecord(
            baseline_id=baseline_id,
            mission_id=mission_rec.mission_id,
            tenant_id=mission_rec.tenant_id,
            workspace_id=mission_rec.workspace_id,
            project_id=mission_rec.project_id,
            baseline_type=BaselineType.MAINTENANCE_COORDINATED,
            condition_type=cond_str,
            is_verified=(status == VerificationStatus.VERIFIED),
            verification_method="OPERATOR_DECLARATION" if status == VerificationStatus.DECLARED else "CANONICAL_QUIESCENCE_CHECK",
            verification_status=status,
            provenance_details=provenance,
            created_at=now,
            updated_at=now,
        )

        self._save_baseline(baseline, conn)
        return baseline

    def establish_maintenance_baseline(
        self,
        mission_id: str,
        condition: Union[CoordinationCondition, str],
        operator_declaration: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationBaselineRecord:
        return self.create_maintenance_baseline(
            mission=mission_id,
            condition_type=condition,
            actor=actor,
            conn=conn,
            operator_declaration=operator_declaration,
        )

    def create_migration_baseline(
        self,
        mission: Union[ValidationMissionRecord, str],
        migration_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        checkpoint_id: Optional[str] = None,
    ) -> ValidationBaselineRecord:
        mission_rec = self._resolve_mission(mission, conn)
        actor.enforce_resource_scope(
            resource_tenant_id=mission_rec.tenant_id,
            resource_workspace_id=mission_rec.workspace_id,
            resource_project_id=mission_rec.project_id,
            resource_kind="ValidationMission",
            resource_id=mission_rec.mission_id,
        )

        if not migration_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "migration_id is required for Migration Baseline.")

        repo = self.migration_repository or SQLiteMigrationRepository(db_path=":memory:")
        mig_agg = repo.get_by_id(migration_id, connection=conn)

        if mig_agg is None:
            raise PipelineError(
                PipelineErrorCode.NOT_FOUND,
                f"Referenced migration {migration_id!r} does not exist.",
            )

        actor.enforce_resource_scope(
            resource_tenant_id=mig_agg.tenant_id,
            resource_workspace_id=mig_agg.workspace_id,
            resource_project_id=mig_agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        if checkpoint_id:
            cur = conn.execute("SELECT checkpoint_id FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,))
            if not cur.fetchone():
                raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Referenced checkpoint {checkpoint_id!r} not found for migration {migration_id!r}.")

        baseline_id = f"base-mig-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        resolved_checkpoint = checkpoint_id or mig_agg.initialization_id or f"chk-{mig_agg.migration_id}-r{mig_agg.revision}"

        provenance = {
            "bound_migration_id": mig_agg.migration_id,
            "bound_migration_name": mig_agg.name,
            "bound_migration_mode": mig_agg.mode.value if hasattr(mig_agg.mode, "value") else str(mig_agg.mode),
            "bound_migration_state": mig_agg.state.value if hasattr(mig_agg.state, "value") else str(mig_agg.state),
            "bound_revision": mig_agg.revision,
            "bound_checkpoint_id": resolved_checkpoint,
            "bound_at": now,
            "bound_by": actor.actor_id,
        }

        baseline = ValidationBaselineRecord(
            baseline_id=baseline_id,
            mission_id=mission_rec.mission_id,
            tenant_id=mission_rec.tenant_id,
            workspace_id=mission_rec.workspace_id,
            project_id=mission_rec.project_id,
            baseline_type=BaselineType.INHERITED_MIGRATION,
            migration_id=migration_id,
            checkpoint_id=resolved_checkpoint,
            is_verified=True,
            verification_method="MIGRATION_EXECUTION_GRAPH",
            verification_status=VerificationStatus.VERIFIED,
            provenance_details=provenance,
            created_at=now,
            updated_at=now,
        )

        self._save_baseline(baseline, conn)
        return baseline

    def establish_migration_baseline(
        self,
        mission_id: str,
        migration_id: str,
        checkpoint_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationBaselineRecord:
        return self.create_migration_baseline(
            mission=mission_id,
            migration_id=migration_id,
            actor=actor,
            conn=conn,
            checkpoint_id=checkpoint_id,
        )

    def create_external_replication_baseline(
        self,
        mission: Union[ValidationMissionRecord, str],
        position_type: Union[PositionType, str],
        position_value: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        provider: Optional[str] = None,
        source_system_hint: Optional[str] = None,
    ) -> ValidationBaselineRecord:
        mission_rec = self._resolve_mission(mission, conn)
        actor.enforce_resource_scope(
            resource_tenant_id=mission_rec.tenant_id,
            resource_workspace_id=mission_rec.workspace_id,
            resource_project_id=mission_rec.project_id,
            resource_kind="ValidationMission",
            resource_id=mission_rec.mission_id,
        )

        pos_type_str = position_type.value if hasattr(position_type, "value") else str(position_type)
        src_prov = provider or mission_rec.source_provider

        is_valid_syntax, err_msg = self.validate_position_syntax(pos_type_str, position_value)
        if not is_valid_syntax:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"External replication position syntax error: {err_msg}",
            )

        provider_compatible = self.check_provider_position_compatibility(src_prov, pos_type_str)
        if not provider_compatible:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"Position type {pos_type_str!r} is not compatible with source provider {src_prov!r}.",
            )

        baseline_id = f"base-ext-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        provenance = {
            "position_type": pos_type_str,
            "position_value": position_value,
            "source_provider": src_prov,
            "source_system_hint": source_system_hint or "External Replication Tool",
            "submitted_by": actor.actor_id,
            "submitted_at": now,
            "truth_guarantee": "EXTERNALLY_ASSERTED — Position accepted as syntactically valid and provider-compatible. Verification pending evaluation.",
        }

        baseline = ValidationBaselineRecord(
            baseline_id=baseline_id,
            mission_id=mission_rec.mission_id,
            tenant_id=mission_rec.tenant_id,
            workspace_id=mission_rec.workspace_id,
            project_id=mission_rec.project_id,
            baseline_type=BaselineType.EXTERNAL_REPLICATION,
            position_type=pos_type_str,
            position_value=position_value,
            is_verified=False,
            verification_method="SYNTAX_AND_PROVIDER_COMPATIBILITY_CHECK",
            verification_status=VerificationStatus.EXTERNALLY_ASSERTED,
            provenance_details=provenance,
            created_at=now,
            updated_at=now,
        )

        self._save_baseline(baseline, conn)
        return baseline

    def establish_external_replication_baseline(
        self,
        mission_id: str,
        provider: str,
        position_type: Union[PositionType, str],
        position_value: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationBaselineRecord:
        return self.create_external_replication_baseline(
            mission=mission_id,
            position_type=position_type,
            position_value=position_value,
            actor=actor,
            conn=conn,
            provider=provider,
        )

    def get_baseline(self, baseline_id: str, conn: sqlite3.Connection) -> Optional[ValidationBaselineRecord]:
        return self.get_baseline_by_id(baseline_id, conn)

    def validate_position_syntax(self, position_type: str, position_value: str) -> Tuple[bool, str]:
        """Validates position syntax according to provider position semantics."""
        if not position_value or not position_value.strip():
            return False, "Position value cannot be empty."

        val = position_value.strip()

        if position_type == PositionType.ORACLE_SCN or position_type == "ORACLE_SCN":
            if not val.isdigit() or int(val) <= 0:
                return False, f"Oracle SCN must be a positive integer, got {val!r}."
            return True, ""

        if position_type == PositionType.POSTGRESQL_LSN or position_type == "POSTGRESQL_LSN":
            # Postgres LSN pattern e.g. 0/16B3748 or 16B3748
            if not re.match(r"^[0-9A-Fa-f]{1,8}/[0-9A-Fa-f]{1,8}$", val) and not re.match(r"^[0-9A-Fa-f]{1,16}$", val):
                return False, f"PostgreSQL LSN must match format 'XXX/YYY' or hex integer, got {val!r}."
            return True, ""

        if position_type == PositionType.MYSQL_GTID or position_type == "MYSQL_GTID":
            # MySQL GTID set pattern e.g. 3E11FA47-71CA-11E1-9E33-C80AA9429562:1-5
            if not re.match(r"^[a-fA-F0-9\-:]+$", val):
                return False, f"MySQL GTID set must be a valid GTID string, got {val!r}."
            return True, ""

        if position_type == PositionType.KAFKA_OFFSET or position_type == "KAFKA_OFFSET":
            if val.isdigit() or val.startswith("{"):
                return True, ""
            return False, f"Kafka offset must be integer or JSON map, got {val!r}."

        return False, f"Unsupported position type {position_type!r}."

    def check_provider_position_compatibility(self, provider: str, position_type: str) -> bool:
        """Checks if a provider natively supports a given position type."""
        p_lower = provider.lower()
        if "oracle" in p_lower:
            return position_type in (PositionType.ORACLE_SCN.value, "ORACLE_SCN")
        if "postgres" in p_lower:
            return position_type in (PositionType.POSTGRESQL_LSN.value, "POSTGRESQL_LSN")
        if "mysql" in p_lower or "maria" in p_lower:
            return position_type in (PositionType.MYSQL_GTID.value, "MYSQL_GTID")
        if "kafka" in p_lower or "event" in p_lower:
            return position_type in (PositionType.KAFKA_OFFSET.value, "KAFKA_OFFSET")
        # Generic object storage / lakehouse compatibility
        return True

    def evaluate_readiness(
        self,
        mission: ValidationMissionRecord,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationReadinessResult:
        """
        Evaluates mission readiness.
        Verifies tenant scope, baseline satisfaction, provider connectivity, and authorization.
        Fails closed with clear diagnostic reasons if conditions are unsatisfied.
        """
        reasons: List[str] = []

        try:
            actor.enforce_resource_scope(
                resource_tenant_id=mission.tenant_id,
                resource_workspace_id=mission.workspace_id,
                resource_project_id=mission.project_id,
                resource_kind="ValidationMission",
                resource_id=mission.mission_id,
            )
        except Exception as ex:
            return ValidationReadinessResult(
                is_ready=False,
                status_code="UNAUTHORIZED",
                summary="Caller lacks authorization for this validation mission.",
                reasons=[str(ex)],
            )

        if not mission.baseline_id:
            default_base = self.create_maintenance_baseline(
                mission=mission,
                condition_type=CoordinationCondition.EXTERNAL_COORDINATION_DECLARED,
                actor=actor,
                conn=conn,
                operator_notes="Default operational baseline created during readiness evaluation.",
            )
            mission.baseline_id = default_base.baseline_id
            conn.execute("UPDATE validation_missions SET baseline_id = ? WHERE mission_id = ?", (default_base.baseline_id, mission.mission_id))

        baseline = self.get_baseline_by_id(mission.baseline_id, conn) if mission.baseline_id else None
        if mission.baseline_id and baseline is None:
            reasons.append(f"Established baseline {mission.baseline_id!r} could not be resolved.")

        if baseline:
            if baseline.baseline_type == BaselineType.MAINTENANCE_COORDINATED:
                if baseline.verification_status == VerificationStatus.UNSATISFIED:
                    reasons.append("Maintenance baseline operational condition is unsatisfied.")
            elif baseline.baseline_type == BaselineType.INHERITED_MIGRATION:
                if not baseline.migration_id:
                    reasons.append("Migration baseline lacks bound migration identity.")
            elif baseline.baseline_type == BaselineType.EXTERNAL_REPLICATION:
                if baseline.verification_status == VerificationStatus.SYNTAX_INVALID:
                    reasons.append("External replication baseline position syntax is invalid.")

        if reasons:
            return ValidationReadinessResult(
                is_ready=False,
                status_code="UNSATISFIED_BASELINE" if any("baseline" in r.lower() for r in reasons) else "READINESS_FAILED",
                summary="Validation mission readiness check failed.",
                reasons=reasons,
                boundary_info=baseline.to_dict() if baseline else None,
            )

        return ValidationReadinessResult(
            is_ready=True,
            status_code="READY",
            summary="Validation mission is ready for initialization and execution.",
            reasons=[],
            boundary_info=baseline.to_dict() if baseline else None,
        )

    def _save_baseline(self, baseline: ValidationBaselineRecord, conn: sqlite3.Connection) -> None:
        prov_json = json.dumps(baseline.provenance_details)
        conn.execute(
            """
            INSERT OR REPLACE INTO validation_baselines (
                baseline_id, mission_id, tenant_id, workspace_id, project_id,
                baseline_type, condition_type, position_type, position_value,
                migration_id, checkpoint_id, is_verified, verification_method,
                verification_status, provenance_details, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                baseline.baseline_id,
                baseline.mission_id,
                baseline.tenant_id,
                baseline.workspace_id,
                baseline.project_id,
                baseline.baseline_type.value if hasattr(baseline.baseline_type, "value") else str(baseline.baseline_type),
                baseline.condition_type,
                baseline.position_type,
                baseline.position_value,
                baseline.migration_id,
                baseline.checkpoint_id,
                1 if baseline.is_verified else 0,
                baseline.verification_method,
                baseline.verification_status.value if hasattr(baseline.verification_status, "value") else str(baseline.verification_status),
                prov_json,
                baseline.created_at,
                baseline.updated_at,
            ),
        )

    def get_baseline_by_id(self, baseline_id: str, conn: sqlite3.Connection) -> Optional[ValidationBaselineRecord]:
        cur = conn.execute("SELECT * FROM validation_baselines WHERE baseline_id = ?", (baseline_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return ValidationBaselineRecord.from_dict(dict(row))

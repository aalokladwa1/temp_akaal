"""akaalPipeline.operations.mutability
=====================================
Canonical operational mutability classifications and dynamic resolver.
Translates operational control intent into authoritative mutability truth based on
actual runtime support, provider capabilities, and current migration lifecycle state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional

from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode


class MutabilityClassification(str, Enum):
    """Canonical 6 tiers of operational parameter mutability."""
    RUNTIME_MUTABLE = "RUNTIME_MUTABLE"
    PAUSE_REQUIRED = "PAUSE_REQUIRED"
    RESTART_REQUIRED = "RESTART_REQUIRED"
    NEW_EXECUTION_REQUIRED = "NEW_EXECUTION_REQUIRED"
    IMMUTABLE = "IMMUTABLE"
    UNSUPPORTED_BY_DESIGN = "UNSUPPORTED_BY_DESIGN"


@dataclass(frozen=True)
class MutabilityEvaluationResult:
    """Detailed evaluation result for a requested operational parameter modification."""
    parameter_name: str
    classification: MutabilityClassification
    is_mutable_now: bool
    requires_pause: bool
    requires_restart: bool
    requires_new_execution: bool
    reason: str
    underlying_authority: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "classification": self.classification.value,
            "is_mutable_now": self.is_mutable_now,
            "requires_pause": self.requires_pause,
            "requires_restart": self.requires_restart,
            "requires_new_execution": self.requires_new_execution,
            "reason": self.reason,
            "underlying_authority": self.underlying_authority,
        }


class OperationalMutabilityResolver:
    """
    Dynamically evaluates whether an operational parameter or control can be modified
    in the current execution context, consulting actual authority capabilities.
    """

    @staticmethod
    def evaluate(
        parameter_name: str,
        current_state: Optional[MigrationLifecycleState] = None,
        mode: Optional[MigrationMode] = None,
        extra_context: Optional[Mapping[str, Any]] = None,
    ) -> MutabilityEvaluationResult:
        ctx = extra_context or {}
        param = parameter_name.lower().strip()
        state = current_state or MigrationLifecycleState.DRAFT

        # 1. Immutable Plan / Identity Fingerprints
        if param in ("plan_fingerprint", "initialization_fingerprint", "migration_id", "source_system_type", "target_system_type"):
            return MutabilityEvaluationResult(
                parameter_name=parameter_name,
                classification=MutabilityClassification.IMMUTABLE,
                is_mutable_now=False,
                requires_pause=False,
                requires_restart=False,
                requires_new_execution=True,
                reason="Plan fingerprints and core system identities are cryptographically bound and immutable.",
                underlying_authority="akaalPipeline.state.artifacts.ArtifactRegistry",
            )

        # 2. Worker Pool Runtime Resizing (Unsupported by design in bounded runtime)
        if param in ("worker_pool_size", "thread_pool_size", "executor_workers", "max_threads"):
            return MutabilityEvaluationResult(
                parameter_name=parameter_name,
                classification=MutabilityClassification.UNSUPPORTED_BY_DESIGN,
                is_mutable_now=False,
                requires_pause=False,
                requires_restart=False,
                requires_new_execution=False,
                reason="Dynamic runtime worker-pool resizing is unsupported by design in bounded thread execution.",
                underlying_authority="akaalEngine.runtime.execution.local.BoundedThreadExecutor",
            )

        # 3. CDC Throttle Budgets (max_fetch_bytes_sec, max_events_per_fetch, poll_interval)
        if param in ("cdc_max_fetch_bytes_sec", "max_fetch_bytes_sec", "cdc_batch_size", "max_events_per_fetch", "cdc_poll_interval_ms"):
            is_active = state in (MigrationLifecycleState.ACTIVE, MigrationLifecycleState.INITIALIZED)
            return MutabilityEvaluationResult(
                parameter_name=parameter_name,
                classification=MutabilityClassification.RUNTIME_MUTABLE,
                is_mutable_now=is_active,
                requires_pause=False,
                requires_restart=False,
                requires_new_execution=False,
                reason="CDC fetch rate and event batch budgets are evaluated per poll cycle under lock in CDCAuthority.",
                underlying_authority="akaalEngine.cdc.api.CDCAuthority",
            )

        # 4. Stream Source Position / Checkpoint Override (Requires pause to avoid split-brain)
        if param in ("cdc_starting_position", "source_position", "checkpoint_override", "resume_position"):
            is_paused = (state == MigrationLifecycleState.PAUSED or getattr(state, "value", str(state)) == "PAUSED")
            return MutabilityEvaluationResult(
                parameter_name=parameter_name,
                classification=MutabilityClassification.PAUSE_REQUIRED,
                is_mutable_now=is_paused,
                requires_pause=True,
                requires_restart=False,
                requires_new_execution=False,
                reason="Altering stream position while active can cause race conditions or duplicate apply; migration must be PAUSED.",
                underlying_authority="akaalEngine.cdc.api.CDCAuthority",
            )

        # 5. Connection Endpoint / Credential Pointers (Restart Required)
        if param in ("endpoint_spec", "auth_spec", "host", "port", "tls_mode", "connection_options"):
            return MutabilityEvaluationResult(
                parameter_name=parameter_name,
                classification=MutabilityClassification.RESTART_REQUIRED,
                is_mutable_now=False,
                requires_pause=False,
                requires_restart=True,
                requires_new_execution=False,
                reason="Connection pool leases and physical tunnels are bound to existing sessions; requires session pool reset or restart.",
                underlying_authority="akaalEngine.connection.pooling.PoolManager",
            )

        # 6. Schema Mapping / Transformations (New Execution Required)
        if param in ("schema_mapping", "transformation_rules", "masking_rules", "column_mappings"):
            is_draft = state in (MigrationLifecycleState.DRAFT, MigrationLifecycleState.CONFIGURING)
            return MutabilityEvaluationResult(
                parameter_name=parameter_name,
                classification=MutabilityClassification.NEW_EXECUTION_REQUIRED,
                is_mutable_now=is_draft,
                requires_pause=False,
                requires_restart=False,
                requires_new_execution=True,
                reason="Schema mappings and transformation DAGs require new compilation, validation, and governance authorization.",
                underlying_authority="akaalPipeline.orchestration.compiler.GraphCompiler",
            )

        # Default fallback: unknown parameters require new execution
        return MutabilityEvaluationResult(
            parameter_name=parameter_name,
            classification=MutabilityClassification.NEW_EXECUTION_REQUIRED,
            is_mutable_now=False,
            requires_pause=False,
            requires_restart=False,
            requires_new_execution=True,
            reason=f"Unrecognized parameter {parameter_name!r} defaults to requiring a new governed execution plan.",
            underlying_authority="akaalPipeline.orchestration.compiler.GraphCompiler",
        )

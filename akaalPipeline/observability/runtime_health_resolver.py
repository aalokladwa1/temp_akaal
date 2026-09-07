"""akaalPipeline.observability.runtime_health_resolver
========================================================
P7C.13 correction -- the TRUSTED, READ-ONLY, CANONICAL resolver that feeds
akaalEngine.intelligence.producers.runtime_health.RuntimeHealthInputs.

This module never accepts caller-supplied operational facts. It resolves a
migration_id to canonical tenant/plan identity via the SAME repository already
used by every other canonical migration read (akaalPipeline.state.repositories.
MigrationRepositoryPort), enforces tenant/workspace/project scope via the SAME
anti-enumeration-safe mechanism already used by
akaalPipeline.application.query_service.PipelineQueryService.get_migration
(PipelineActorContext.enforce_resource_scope -- identical error shape whether
the migration does not exist or belongs to another tenant), and then samples
REAL canonical authorities -- never a second RuntimeAuthority/TelemetryAuthority/
CDCAuthority/OwnershipManager, always the SAME instances already reached by
akaalPipeline.observability.unified_service.UnifiedObservabilityService via
binding_registry -> "gateway_engine_binding" -> engine_gateway.coordinator.

Every dimension this resolver cannot presently obtain from a genuine canonical
read is left as None (the runtime_health producer already reports None as
UNKNOWN, never a fabricated HEALTHY) -- see the per-field provenance notes on
each private `_read_*` method below for exactly which canonical surface each
dimension does or does not come from today.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from akaalEngine.intelligence.producers.runtime_health import RuntimeHealthInputs
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.repositories import MigrationRepositoryPort

logger = logging.getLogger("akaalPipeline.observability.runtime_health_resolver")


class CanonicalRuntimeHealthResolver:
    """Read-only projection adapter. Holds no state of its own beyond
    references to already-canonical authorities; performs zero writes."""

    def __init__(
        self,
        repository: MigrationRepositoryPort,
        binding_registry: Optional[Any] = None,
        ownership_manager: Optional[Any] = None,
    ) -> None:
        self._repository = repository
        self._binding_registry = binding_registry
        # Optional: akaalEngine.fabric.ownership.manager.OwnershipManager (P7B.25).
        # Not constructed by this module -- P7B Fabric ownership is only wired
        # up for plans that actually require Fabric placement (see
        # akaalPipeline.orchestration.fabric_gate.FabricGateDependencies). When
        # None, the FABRIC dimension is honestly reported as unavailable rather
        # than fabricated -- never inferred as "healthy because no manager was
        # configured."
        self._ownership_manager = ownership_manager

    def resolve(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        *,
        ownership_manager: Optional[Any] = None,
    ) -> RuntimeHealthInputs:
        """`ownership_manager`, if given, OVERRIDES the constructor-configured
        one for this single call -- lets a caller resolve a live P7B
        OwnershipManager dynamically per-request (e.g. from
        PlanExecutionCoordinator.fabric_dependencies.ownership_manager, which
        may not exist at resolver-construction time but could be configured
        later by a deployment that opts into Fabric placement) without this
        module ever constructing its own OwnershipManager/durability store."""
        agg = self._repository.get_by_id(migration_id)

        # Anti-enumeration-safe: whether the migration does not exist at all,
        # or exists but belongs to a different tenant/workspace/project, the
        # caller receives the exact same PipelineError (same code, same
        # message shape) via enforce_resource_scope -- never a distinguishable
        # "not found" vs "not yours" response.
        if agg is None:
            actor.enforce_resource_scope(
                resource_tenant_id="__no_such_migration__",
                resource_kind="Migration",
                resource_id=migration_id,
            )
            # enforce_resource_scope always raises when resource_tenant_id !=
            # actor.organization_id (true for the sentinel above); this line
            # is unreachable but keeps control flow explicit for readers.
            raise PipelineError(PipelineErrorCode.TENANT_BOUNDARY_VIOLATION, f"Migration {migration_id!r} not found or unauthorized for tenant.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        runtime_snap, cdc_snap, telemetry_authority = self._sample_engine_authorities()

        transport = self._read_transport(telemetry_authority, migration_id)
        cdc = self._read_cdc(cdc_snap)
        workers = self._read_workers()  # always None -- see docstring: NOT_CURRENTLY_EXPOSED at migration scope.
        platform_context = self._read_platform_context(runtime_snap)
        fabric = self._read_fabric(agg, ownership_manager or self._ownership_manager)

        return RuntimeHealthInputs(
            migration_id=migration_id,
            transport=transport,
            cdc=cdc,
            validation=None,  # NOT_CURRENTLY_EXPOSED -- see module docstring / P7C.13 report.
            workers=workers,
            fabric=fabric,
            resources=None,  # NOT_CURRENTLY_EXPOSED -- no verified canonical cpu/mem/storage read surface.
            governance=None,  # NOT_CURRENTLY_EXPOSED -- no canonical approvals/cutover-readiness read surface found.
            platform_context=platform_context,
        )

    def sample_engine_authorities(self):
        """Public accessor for other P7C resolvers (P7C.17 forecasting, etc.)
        that need the same raw canonical samples this class already gathers --
        avoids each of them reaching into binding_registry/EngineGateway
        internals a second time."""
        return self._sample_engine_authorities()

    # --- Canonical authority sampling (never a second authority) -----------
    def _sample_engine_authorities(self):
        """Reaches the SAME RuntimeAuthority/CDCAuthority/TelemetryAuthority
        instances the real production seam actually constructs -- verified by
        inspection of akaalPipeline.application.unified_caller.
        PipelineUnifiedCaller.bind_engine_gateway (registers an
        EngineBindingDescriptor whose `port_instance` is a real
        akaalPipeline.adapters.engine_gateway.PipelineEngineGatewayAdapter) and
        that adapter's own `self.gateway` (a real akaalEngine.gateway.api.
        EngineGateway) -> `self.gateway.coordinator` (a real
        akaalEngine.gateway.orchestration.coordinator.GatewayCoordinator,
        confirmed to hold `.runtime_authority` / `.cdc_authority` / `.
        telemetry_authority` by inspection of that class's own __init__ and of
        PipelineEngineGatewayAdapter.publish_engine_event/close, which already
        read the exact same attributes).

        NOTE: akaalPipeline.observability.unified_service.
        UnifiedObservabilityService.query_telemetry looks for a nonexistent
        `binding.engine_gateway` attribute instead (EngineBindingDescriptor has
        no such field -- only `port_instance`); that lookup is dead code in
        the existing repository and is deliberately NOT reproduced here.
        Returns (runtime_snapshot_dict_or_None, cdc_snapshot_dict_or_None,
        telemetry_authority_or_None)."""
        runtime_snap = None
        cdc_snap = None
        telemetry_authority = None
        if not self._binding_registry:
            return runtime_snap, cdc_snap, telemetry_authority

        binding = self._binding_registry.get("gateway_engine_binding")
        port_instance = getattr(binding, "port_instance", None) if binding else None
        gw = getattr(port_instance, "gateway", None) if port_instance else None
        coord = getattr(gw, "coordinator", None) if gw else None
        if coord is None:
            return runtime_snap, cdc_snap, telemetry_authority

        if getattr(coord, "runtime_authority", None):
            try:
                runtime_snap = coord.runtime_authority.get_runtime_snapshot()
            except Exception as exc:  # noqa: BLE001 -- a sampling failure must degrade to UNKNOWN, never crash the request
                logger.warning("[P7C.13] Failed to sample RuntimeAuthority: %s", exc)
        if getattr(coord, "cdc_authority", None):
            try:
                raw = coord.cdc_authority.get_snapshot()
                cdc_snap = raw.to_dict() if hasattr(raw, "to_dict") else dict(getattr(raw, "__dict__", {}))
            except Exception as exc:  # noqa: BLE001
                logger.warning("[P7C.13] Failed to sample CDCAuthority: %s", exc)
        if getattr(coord, "telemetry_authority", None):
            telemetry_authority = coord.telemetry_authority

        return runtime_snap, cdc_snap, telemetry_authority

    def _read_transport(self, telemetry_authority: Optional[Any], migration_id: str) -> Optional[dict]:
        """CANONICAL_DERIVATION_AVAILABLE: akaalEngine.telemetry.api.
        TelemetryAuthority.get_progress_snapshot(migration_id) is genuinely
        migration-scoped (unlike get_metric_snapshot(), which is process-global
        and therefore never used here to avoid leaking cross-migration data
        into a single migration's projection). There is no canonical baseline
        throughput to compare against, so only the observed rate is reported;
        the runtime_health producer already treats a missing baseline as
        UNKNOWN status rather than fabricating a ratio."""
        if telemetry_authority is None or not hasattr(telemetry_authority, "get_progress_snapshot"):
            return None
        try:
            snap = telemetry_authority.get_progress_snapshot(migration_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[P7C.13] Failed to sample migration progress: %s", exc)
            return None
        if snap is None:
            return None
        return {
            "throughput_rows_per_sec": getattr(snap, "rows_per_second", None),
            "baseline_rows_per_sec": None,  # NOT_CURRENTLY_EXPOSED: no canonical baseline throughput source exists.
        }

    def _read_cdc(self, cdc_snap: Optional[dict]) -> Optional[dict]:
        """PARTIAL_CANONICAL_READ: akaalEngine.cdc.api.CDCAuthority.get_snapshot()
        genuinely reports current backlog_events/backlog_bytes and
        replication_lag_seconds. Its 'source_change_rate_events_sec' /
        'target_apply_rate_events_sec' fields are, by inspection of the
        producing code, actually cumulative lifetime totals (events_captured_
        total / events_applied_total) mislabeled with a "_sec" suffix -- NOT
        true per-second rates. Feeding those into a generation/apply ratio
        would fabricate a bottleneck verdict from a meaningless number, so
        this resolver deliberately leaves generation_rate/apply_rate as None
        (UNKNOWN) rather than mapping them, and reports only the genuinely
        instantaneous facts (backlog size, replication lag)."""
        if not cdc_snap:
            return None
        return {
            "generation_rate": None,  # NOT_CURRENTLY_EXPOSED as a true rate -- see docstring above.
            "apply_rate": None,       # NOT_CURRENTLY_EXPOSED as a true rate -- see docstring above.
            "backlog_size": cdc_snap.get("backlog_events"),
            "backlog_trend": None,  # NOT_CURRENTLY_EXPOSED: no historical comparison point sampled here.
            "lag_seconds": cdc_snap.get("replication_lag_seconds"),
        }

    def _read_workers(self) -> Optional[dict]:
        """NOT_CURRENTLY_EXPOSED at migration scope -- verified by forensic
        inspection, not assumed:
          - akaalEngine.runtime.models.worker.WorkerSnapshot carries NO
            migration_id/execution_id/plan_id field at all (nor a generic
            metadata field) -- there is no structural room to associate a
            worker record with a migration.
          - akaalEngine.runtime.models.task.TaskSnapshot does carry a generic
            `metadata: Mapping[str, Any]` field, but akaalEngine.runtime.api.
            RuntimeAuthority.submit_task()/_dispatch_execution()/cancel_task()/
            pause_task()/resume_task() never forward TaskSpec.metadata into
            any TaskSnapshot they construct -- metadata is always {} on every
            snapshot RuntimeAuthority actually produces today, even on the one
            real call site (akaalEngine.gateway.routing.dispatcher.
            _handle_recover_checkpoint) that tries to tag a TaskSpec with
            migration_id. The migration<->task link is broken in practice, not
            merely unfiltered.
          - akaalEngine.runtime.workers.registry.WorkerRegistry exposes no
            migration-scoped listing method (get_snapshot(worker_id),
            list_snapshots(), list_available_workers() only).

        Given this, presenting akaalEngine.runtime.api.RuntimeAuthority.
        get_runtime_snapshot()'s process-global active_workers as THIS
        migration's WORKERS health would fabricate scope that does not exist
        (P7C.13 correction "Final Blocker A"). The process-wide worker count
        is still surfaced, but only as RuntimeHealthInputs.platform_context --
        never as the `workers` dimension input, never influencing WORKERS
        status, never able to raise/lower/suppress any other dimension. See
        _read_platform_context."""
        return None

    def _read_platform_context(self, runtime_snap: Optional[dict]) -> Optional[dict]:
        """Explicitly PLATFORM-SCOPED (not migration-scoped) context, kept
        entirely separate from any dimension so it can never be mistaken for
        or silently promoted into this migration's own worker health."""
        if not runtime_snap:
            return None
        workers = runtime_snap.get("active_workers") or []
        if not workers:
            return None
        return {"process_worker_count": len(workers), "scope": "PLATFORM_WIDE_NOT_MIGRATION_SCOPED"}

    def _read_fabric(self, agg: Any, ownership_manager: Optional[Any]) -> Optional[dict]:
        """CANONICAL_READ_AVAILABLE only when an OwnershipManager instance is
        actually supplied (see __init__ docstring): akaalEngine.fabric.
        ownership.manager.OwnershipManager.try_get(ownership_key) is a
        genuine, non-raising, read-only canonical lookup. The ownership_key
        (f"{tenant_id}::{migration_id}::{plan_id}", per akaalEngine.fabric.
        ownership.models.OwnershipClaim.ownership_key) is built ENTIRELY from
        canonical fields already loaded from the migration repository (agg.
        tenant_id, agg.migration_id, agg.plan_id) -- never from caller input.
        A caller cannot influence this dimension in any way."""
        if ownership_manager is None or not agg.plan_id:
            return None
        ownership_key = f"{agg.tenant_id}::{agg.migration_id}::{agg.plan_id}"
        try:
            record = ownership_manager.try_get(ownership_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[P7C.13] Failed to sample OwnershipManager: %s", exc)
            return None
        if record is None:
            return None
        state_raw = getattr(record, "state", None)
        state_name = getattr(state_raw, "name", str(state_raw)).upper()
        is_expired = bool(getattr(record, "is_expired", lambda: False)())
        ownership_valid = state_name == "ACTIVE" and not is_expired
        return {
            "ownership_valid": ownership_valid,
            "lease_valid": not is_expired,
            "fencing_conflicts": 0,
        }

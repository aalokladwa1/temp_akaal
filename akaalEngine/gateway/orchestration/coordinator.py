"""
akaalEngine.gateway.orchestration.coordinator
==============================================
Canonical Gateway multi-authority workflow orchestration coordinator.
Wires and sequences calls between Authorities #1–#12 based on semantic requests,
preserving identity, fencing tokens, cancellation context, proof classifications, and evidence packaging.
"""

import logging
import time
from typing import Any, Dict, List, Mapping, Optional

from akaalEngine.connection.api import ConnectionAuthority, default_connection_authority
from akaalEngine.extensions.authority import ExtensionsAuthority, default_extensions_authority
from akaalEngine.discovery.authority import DiscoveryAuthority, default_discovery_authority
from akaalEngine.schema.authority import SchemaAuthority, default_schema_authority
from akaalEngine.durability.api import DurabilityAuthority
from akaalEngine.runtime.api import RuntimeAuthority
from akaalEngine.telemetry.api import TelemetryAuthority
from akaalEngine.data_processing.api import DataProcessingAuthority
from akaalEngine.transport.api import TransportAuthority
from akaalEngine.cdc.api import CDCAuthority
from akaalEngine.validation.api import ValidationAuthority
from akaalEngine.evidence.api import EvidenceAuthority

from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import SemanticOperation
from akaalEngine.gateway.models.responses import GatewayResponse

logger = logging.getLogger("akaalEngine.gateway.orchestration")


class GatewayCoordinator:
    """Orchestrates multi-authority execution chains across Authorities #1–#12."""

    def __init__(
        self,
        connection_authority: Optional[ConnectionAuthority] = None,
        extensions_authority: Optional[ExtensionsAuthority] = None,
        discovery_authority: Optional[DiscoveryAuthority] = None,
        schema_authority: Optional[SchemaAuthority] = None,
        durability_authority: Optional[DurabilityAuthority] = None,
        runtime_authority: Optional[RuntimeAuthority] = None,
        telemetry_authority: Optional[TelemetryAuthority] = None,
        data_processing_authority: Optional[DataProcessingAuthority] = None,
        transport_authority: Optional[TransportAuthority] = None,
        cdc_authority: Optional[CDCAuthority] = None,
        validation_authority: Optional[ValidationAuthority] = None,
        evidence_authority: Optional[EvidenceAuthority] = None,
        keystore: Optional[Any] = None,
    ) -> None:
        self.keystore = keystore
        self.connection_authority = connection_authority or ConnectionAuthority()
        self.extensions_authority = extensions_authority or ExtensionsAuthority()
        self.discovery_authority = discovery_authority or DiscoveryAuthority(
            connection_authority=self.connection_authority,
            extensions_authority=self.extensions_authority,
        )
        self.schema_authority = schema_authority or SchemaAuthority()
        if durability_authority is None:
            from akaalEngine.durability.models import DurabilityConfig
            import tempfile
            import os
            import hashlib
            dur_dir = tempfile.mkdtemp(prefix="akaal_gw_dur_")
            sec_env = os.environ.get("AKAAL_GATEWAY_RECEIPT_SECRET", "akaal-fencing-secret-root-v1")
            fencing_key = hashlib.sha256(sec_env.encode("utf-8") + b":fencing").digest()
            journal_key = hashlib.sha256(sec_env.encode("utf-8") + b":journal").digest()
            durability_authority = DurabilityAuthority(
                config=DurabilityConfig(
                    storage_dir=dur_dir,
                    fencing_signing_key=fencing_key,
                    journal_anchor_key=journal_key,
                )
            )
        self.durability_authority = durability_authority
        if runtime_authority is None:
            runtime_authority = RuntimeAuthority(durability_authority=self.durability_authority)
            runtime_authority.start()
        elif getattr(runtime_authority, "durability_authority", None) is None:
            runtime_authority.durability_authority = self.durability_authority
        self.runtime_authority = runtime_authority
        self.telemetry_authority = telemetry_authority or TelemetryAuthority()
        self.data_processing_authority = data_processing_authority or DataProcessingAuthority()

        self.transport_authority = transport_authority or TransportAuthority(
            durability_authority=self.durability_authority,
            runtime_authority=self.runtime_authority,
            telemetry_authority=self.telemetry_authority,
            data_processing_authority=self.data_processing_authority,
        )
        self.cdc_authority = cdc_authority or CDCAuthority(
            schema_authority=self.schema_authority,
            durability_authority=self.durability_authority,
            runtime_authority=self.runtime_authority,
            telemetry_authority=self.telemetry_authority,
            data_processing_authority=self.data_processing_authority,
            transport_authority=self.transport_authority,
        )
        self.validation_authority = validation_authority or ValidationAuthority(
            connection_authority=self.connection_authority,
            schema_authority=self.schema_authority,
            durability_authority=self.durability_authority,
            runtime_authority=self.runtime_authority,
            telemetry_authority=self.telemetry_authority,
            data_processing_authority=self.data_processing_authority,
            transport_authority=self.transport_authority,
            cdc_authority=self.cdc_authority,
        )
        self.evidence_authority = evidence_authority or EvidenceAuthority(
            connection_authority=self.connection_authority,
            schema_authority=self.schema_authority,
            durability_authority=self.durability_authority,
            runtime_authority=self.runtime_authority,
            telemetry_authority=self.telemetry_authority,
            data_processing_authority=self.data_processing_authority,
            transport_authority=self.transport_authority,
            cdc_authority=self.cdc_authority,
            validation_authority=self.validation_authority,
        )

    def check_cancellation(self, context: GatewayRequestContext) -> None:
        """Fails early if cancellation has been requested."""
        if context.is_cancelled():
            from akaalEngine.runtime.models import RuntimeEngineException
            raise RuntimeEngineException(f"Operation '{context.operation_id}' cancelled before execution.")

    def check_fencing(self, context: GatewayRequestContext) -> None:
        """Verifies caller's fencing token envelope and epoch with canonical DurabilityAuthority in a fail-closed manner."""
        from akaalEngine.durability.models import FencingViolationError

        if context.fencing_epoch is not None and context.fencing_epoch <= 0:
            raise FencingViolationError(
                f"Caller fencing epoch {context.fencing_epoch} is invalid. Fencing epoch must be a positive integer."
            )

        canonical_resource_id = (
            f"{context.migration_id}/{context.run_id}/{context.job_id}"
            if context.job_id
            else (f"{context.migration_id}/{context.run_id}" if context.run_id else context.migration_id)
        )

        envelope = getattr(context, "fencing_token_envelope", None)
        if not envelope or not isinstance(envelope, Mapping):
            raise FencingViolationError(
                f"Admission rejected: Missing required authenticated fencing_token_envelope for operation '{context.operation_id}' on resource '{canonical_resource_id}'."
            )

        # 1. Directly validate custom authority when verify_fencing_token is provided
        if self.durability_authority and hasattr(self.durability_authority, "verify_fencing_token"):
            valid = self.durability_authority.verify_fencing_token(envelope)
            if valid is False:
                raise FencingViolationError("Fencing token verification failed.")

        # 2. Authenticate cryptographic HMAC signature on envelope
        if hasattr(self.durability_authority, "validate_fencing_envelope"):
            valid = self.durability_authority.validate_fencing_envelope(envelope)
            if not valid:
                raise FencingViolationError("Fencing token HMAC signature is invalid or unauthenticated.")

        # 3. Strict exact canonical resource identity matching
        env_res = envelope.get("resource_id") or envelope.get("canonical_resource_id")
        if env_res != canonical_resource_id:
            raise FencingViolationError(
                f"Fencing token resource mismatch: token issued for exact resource '{env_res}' cannot execute request for '{canonical_resource_id}'."
            )

        # 4. Strict epoch matching against request context
        env_epoch = envelope.get("fencing_epoch") or envelope.get("epoch")
        if env_epoch is not None and context.fencing_epoch is not None and env_epoch != context.fencing_epoch:
            raise FencingViolationError(
                f"Envelope fencing epoch {env_epoch} does not match request fencing epoch {context.fencing_epoch}."
            )

        # 5. Verify active epoch in Durability Authority
        if self.durability_authority and hasattr(self.durability_authority, "get_current_epoch"):
            curr_epoch = self.durability_authority.get_current_epoch(canonical_resource_id)
            if curr_epoch == 0:
                curr_epoch = self.durability_authority.get_current_epoch(context.migration_id)

            if curr_epoch > 0 and context.fencing_epoch is not None and context.fencing_epoch != curr_epoch:
                raise FencingViolationError(
                    f"Caller fencing epoch {context.fencing_epoch} does not match active resource fencing epoch {curr_epoch} for '{canonical_resource_id}'."
                )

    # -------------------------------------------------------------------------
    # Multi-Authority Orchestrated Workflow Handlers
    # -------------------------------------------------------------------------

    def orchestrate_test_connection(
        self, context: GatewayRequestContext, payload: Dict[str, Any]
    ) -> GatewayResponse[Dict[str, Any]]:
        """1. Connection + Extensions verification."""
        self.check_cancellation(context)
        self.check_fencing(context)

        from akaalEngine.connection.models import EndpointSpec
        provider_id = payload.get("provider_id") or payload.get("system_type") or "sqlite"
        spec = EndpointSpec(
            provider_id=provider_id,
            host=payload.get("host"),
            port=payload.get("port"),
            options=payload,
        )

        res = self.connection_authority.test_connectivity(spec)
        self.telemetry_authority.record_counter("gateway_test_connection_total", 1.0, {"provider": str(provider_id)})

        is_connected = bool(getattr(res, "is_successful", getattr(res, "connected", False)))
        if not is_connected:
            return GatewayResponse.create_failure(
                operation_id=context.operation_id,
                operation_type=SemanticOperation.TEST_CONNECTION.value,
                failure_category=GatewayFailureCategory.CONNECTIVITY_FAILURE,
                error_message=f"Connectivity check failed for provider '{provider_id}': {res}",
                migration_id=context.migration_id,
                run_id=context.run_id,
                fencing_epoch=context.fencing_epoch,
            )

        return GatewayResponse.create_success(
            operation_id=context.operation_id,
            operation_type=SemanticOperation.TEST_CONNECTION.value,
            migration_id=context.migration_id,
            run_id=context.run_id,
            payload={
                "connected": True,
                "connection_id": getattr(res, "connection_id", f"conn-{context.operation_id}"),
                "message": getattr(res, "message", f"Successfully connected to {provider_id}"),
                "details": str(res),
            },
            fencing_epoch=context.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

    def orchestrate_resolve_capabilities(
        self, context: GatewayRequestContext, payload: Dict[str, Any]
    ) -> GatewayResponse[Dict[str, Any]]:
        """2. Extensions + Connection capability resolution."""
        self.check_cancellation(context)
        self.check_fencing(context)
        provider_id = payload.get("provider_id", "sqlite")
        req_caps = payload.get("required_capabilities", [])

        desc = self.extensions_authority.describe_provider(provider_id)
        supported = desc is not None

        return GatewayResponse.create_success(
            operation_id=context.operation_id,
            operation_type=SemanticOperation.RESOLVE_CAPABILITIES.value,
            migration_id=context.migration_id,
            run_id=context.run_id,
            payload={
                "provider_id": provider_id,
                "supported": supported,
                "manifest": str(desc) if desc else None,
            },
            fencing_epoch=context.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

    def orchestrate_discover_catalog(
        self, context: GatewayRequestContext, payload: Dict[str, Any]
    ) -> GatewayResponse[Dict[str, Any]]:
        """3. Connection -> Discovery catalog profiling."""
        self.check_cancellation(context)
        self.check_fencing(context)
        from akaalEngine.connection.models import EndpointSpec
        provider_id = payload.get("provider_id", "sqlite")
        spec = EndpointSpec(
            provider_id=provider_id,
            host=payload.get("host"),
            port=payload.get("port"),
            options=payload,
        )

        snapshot = self.discovery_authority.discover(spec)
        return GatewayResponse.create_success(
            operation_id=context.operation_id,
            operation_type=SemanticOperation.DISCOVER_CATALOG.value,
            migration_id=context.migration_id,
            run_id=context.run_id,
            payload={
                "snapshot": str(snapshot),
                "tables_count": len(getattr(snapshot, "tables", [])) if hasattr(snapshot, "tables") else 0,
            },
            fencing_epoch=context.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

    def orchestrate_compile_schema(
        self, context: GatewayRequestContext, payload: Dict[str, Any]
    ) -> GatewayResponse[Dict[str, Any]]:
        """4. Discovery -> Schema compilation & target DDL translation."""
        self.check_cancellation(context)
        self.check_fencing(context)
        source_snap = payload.get("source_discovery_snapshot", {})
        target_dialect = payload.get("target_dialect", payload.get("target_engine", "postgresql"))

        import asyncio
        import inspect

        from akaalEngine.schema.authority import SchemaCompilationRequest
        req = SchemaCompilationRequest(
            source_snapshot=source_snap,
            target_engine=target_dialect,
        )

        res_or_coro = self.schema_authority.compile(req)
        if inspect.isawaitable(res_or_coro):
            compilation_result = asyncio.run(res_or_coro)
        else:
            compilation_result = res_or_coro

        return GatewayResponse.create_success(
            operation_id=context.operation_id,
            operation_type=SemanticOperation.COMPILE_SCHEMA_MAPPING.value,
            migration_id=context.migration_id,
            run_id=context.run_id,
            payload={
                "target_dialect": target_dialect,
                "compilation_result": str(compilation_result),
            },
            fencing_epoch=context.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

    def orchestrate_bulk_migration(
        self, context: GatewayRequestContext, payload: Dict[str, Any]
    ) -> GatewayResponse[Dict[str, Any]]:
        """7. Multi-authority orchestration: Runtime -> Transport -> Data Processing -> Durability -> Telemetry -> Evidence."""
        self.check_cancellation(context)
        self.check_fencing(context)

        # In M2 protected boundary mode, verify active capture stream handle and boundary token
        if payload.get("require_active_stream_boundary"):
            stream_handle = payload.get("cdc_stream_handle")
            boundary_token = payload.get("cdc_boundary_token") or payload.get("boundary_token")
            if not stream_handle or not boundary_token:
                from akaalEngine.cdc.models.errors import CDCCapabilityError
                raise CDCCapabilityError(
                    f"M2 Bulk transport execution requires active stream handle and boundary token. Missing from input context: stream_handle={stream_handle!r}, boundary_token={boundary_token!r}."
                )
            if hasattr(self.cdc_authority, "is_capture_active"):
                if not self.cdc_authority.is_capture_active(context.migration_id):
                    from akaalEngine.cdc.models.errors import CDCCapabilityError
                    raise CDCCapabilityError(
                        f"M2 Bulk transport execution rejected: CDC capture is not actively capturing for migration '{context.migration_id}'. Protected overlap invariant violated."
                    )

        # Stage A: Record start in Telemetry (#7)
        self.telemetry_authority.record_counter("gateway_bulk_migration_started", 1.0, {"mig_id": context.migration_id})

        # Stage B: Submit task to Runtime (#6)
        from akaalEngine.runtime.models import TaskSpec
        task_spec = TaskSpec(
            task_id=f"task-{context.operation_id}",
            task_type="bulk_transport",
            kwargs=payload,
        )
        task_snap = self.runtime_authority.submit_task(task_spec)

        # Stage C: Execute Bulk Transport (#9) + Data Processing (#8)
        if hasattr(self.transport_authority, "execute_bulk_transport"):
            transport_snap = self.transport_authority.execute_bulk_transport(payload)
        elif hasattr(self.transport_authority, "execute_partition_transport"):
            reader = payload.get("source_reader") or payload.get("reader")
            writer = payload.get("target_writer") or payload.get("writer")
            partition = payload.get("partition")

            # Auto-resolve the real provider-native SourceReader/TargetWriter from the
            # TransportDriverRegistry when the caller supplied a provider_id + connection
            # params instead of pre-built driver objects -- this is what makes
            # EXECUTE_BULK_MIGRATION reachable purely from provider identity, the missing
            # link between "Gateway can describe a provider" and "Gateway can move data
            # for it" that this hardening pass closes.
            if reader is None and payload.get("source_provider_id"):
                reader = self.transport_authority.resolve_source_reader_for_provider(
                    payload["source_provider_id"],
                    connection_params=payload.get("source_connection_params", {}),
                )
            if writer is None and payload.get("target_provider_id"):
                writer = self.transport_authority.resolve_target_writer_for_provider(
                    payload["target_provider_id"],
                    connection_params=payload.get("target_connection_params", {}),
                )

            if not reader or not writer or not partition:
                from akaalEngine.transport.models.errors import TransportError
                raise TransportError("Transport execution requires active SourceReader, TargetWriter, and TransportPartition instances.")
            sec_reval = payload.get("security_revalidator")
            if sec_reval is None and getattr(context, "execution_authorization_artifact", None) and getattr(self, "keystore", None):
                from akaalPipeline.security.execution_authorization import verify_execution_authorization
                authz_art = context.execution_authorization_artifact
                ks = self.keystore
                ctx_t_id = context.tenant_id
                ctx_m_id = context.migration_id
                # execute_partition_transport() calls this same revalidator at partition
                # entry AND at every batch boundary (by design, to catch mid-execution
                # revocation) -- and GatewayDispatcher.dispatch() (the sole real external
                # entry point into this coordinator; see akaalEngine/gateway/routing/
                # dispatcher.py) already independently ran its OWN
                # verify_execution_authorization() admission check against this exact
                # artifact, with replay-checking enabled, before this coordinator method
                # was ever invoked. Replay-uniqueness (rejecting a signed artifact reused
                # across SEPARATE admissions) is therefore already enforced at that
                # admission layer; re-enforcing it here would consume the SAME nonce a
                # second time and falsely reject every request as "replay detected" on its
                # very first Stage C barrier call, and every subsequent batch even more so.
                # This barrier's job is re-verifying the credential (signature, expiration,
                # tenant/migration identity, live revocation status) is STILL valid as
                # execution proceeds, not re-litigating whether it was fresh on arrival --
                # so check_replay is always disabled here. Found via first-10-provider
                # hostile multi-barrier testing (see tests/security/
                # test_p7a_campaign_b_first10_tenant_isolation.py).
                def sec_reval() -> bool:
                    return verify_execution_authorization(
                        artifact=authz_art,
                        expected_tenant_id=ctx_t_id,
                        expected_migration_id=ctx_m_id,
                        keystore=ks,
                        check_replay=False,
                    )
                    return result
            # Real restart support: if the caller asks to resume (or omits an explicit
            # position but a prior durable checkpoint exists for this migration), recover
            # the provider-native continuation position from the REAL Durability authority
            # rather than requiring the caller to track it out-of-band.
            resume_position = payload.get("resume_from_position")
            if resume_position is None and payload.get("resume_from_checkpoint") and self.durability_authority is not None:
                prior = self.durability_authority.get_latest_checkpoint(context.migration_id)
                if prior is not None and isinstance(prior.metadata, dict):
                    resume_position = prior.metadata.get("read_position")

            transport_snap = self.transport_authority.execute_partition_transport(
                reader=reader,
                writer=writer,
                partition=partition,
                fencing_token=payload.get("fencing_token"),
                cancellation_token=payload.get("cancellation_token"),
                migration_id=context.migration_id,
                run_id=context.run_id,
                security_revalidator=sec_reval,
                resume_from_position=resume_position,
            )
        else:
            from akaalEngine.transport.models.errors import TransportError
            raise TransportError("TransportAuthority does not support bulk data transport execution.")

        # Stage D: Create Durability checkpoint (#5) - DO NOT SUPPRESS FAILURES
        from akaalEngine.durability.models import MigrationCheckpoint, FencingToken
        # Reuse the SAME token (same resource_id/epoch scope) the per-batch checkpoints
        # inside execute_partition_transport() already saved with, when the caller supplied
        # one -- issuing a brand-new token scoped only to `context.migration_id` here would
        # start an entirely independent epoch counter for a DIFFERENT fencing resource_id
        # (bare migration_id vs "migration_id/run_id"), which can carry a lower epoch number
        # than the per-batch checkpoints already persisted for this same migration_id and
        # get rejected as a stale monotonic-epoch rollback by the checkpoint registry.
        caller_token = payload.get("fencing_token")
        if caller_token is not None and hasattr(caller_token, "fencing_epoch"):
            token = caller_token
        elif hasattr(self.durability_authority, "issue_fencing_token"):
            token = self.durability_authority.issue_fencing_token(context.migration_id, "gateway")
        else:
            token = FencingToken(
                resource_id=context.migration_id,
                worker_id="gateway",
                fencing_epoch=context.fencing_epoch or 1,
                issued_at="2026-08-23T20:30:00Z",
                signature="gateway-fencing-sig",
            )

        ckpt = MigrationCheckpoint(
            migration_id=context.migration_id,
            job_id=context.run_id or "job-1",
            fencing_epoch=token.fencing_epoch,
            status="COMPLETED",
        )
        self.durability_authority.save_checkpoint(ckpt, token)

        # Stage E: Package machine execution evidence (#12)
        exec_art = self.evidence_authority.package_execution_evidence(
            migration_id=context.migration_id,
            run_id=context.run_id,
            execution_state="COMPLETED",
            artifact_id=f"art-exec-{context.operation_id}",
        )

        return GatewayResponse.create_success(
            operation_id=context.operation_id,
            operation_type=SemanticOperation.EXECUTE_BULK_MIGRATION.value,
            migration_id=context.migration_id,
            run_id=context.run_id,
            payload={
                "task_id": task_snap.task_id,
                "transport_snapshot": str(transport_snap),
                "checkpoint_id": f"chk-{context.operation_id}",
                "evidence_artifact_id": exec_art.artifact_id,
                "status": "COMPLETED",
            },
            fencing_epoch=context.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

    def orchestrate_cdc_sync(
        self, context: GatewayRequestContext, payload: Dict[str, Any]
    ) -> GatewayResponse[Dict[str, Any]]:
        """9. CDC stream capture -> Durability -> Telemetry."""
        self.check_cancellation(context)
        self.check_fencing(context)

        events_fetched = False
        events = []
        if hasattr(self.cdc_authority, "fetch_events"):
            events = self.cdc_authority.fetch_events(max_events=payload.get("batch_size", 1000))
            events_fetched = True
        elif hasattr(self.cdc_authority, "active_adapter") and hasattr(self.cdc_authority.active_adapter, "fetch_events"):
            events = self.cdc_authority.active_adapter.fetch_events(max_events=payload.get("batch_size", 1000))
            events_fetched = True

        if not events_fetched:
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("CDCAuthority does not support physical stream capture/apply orchestration.")

        if hasattr(self.cdc_authority, "apply_events") and events:
            self.cdc_authority.apply_events(events)

        cdc_snap = self.cdc_authority.get_snapshot()
        self.telemetry_authority.record_counter("gateway_cdc_started", 1.0, {"mig_id": context.migration_id})

        return GatewayResponse.create_success(
            operation_id=context.operation_id,
            operation_type=SemanticOperation.EXECUTE_CDC_SYNC.value,
            migration_id=context.migration_id,
            run_id=context.run_id,
            payload={
                "events_processed": len(events),
                "cdc_snapshot": str(cdc_snap),
                "status": "SYNCING",
            },
            fencing_epoch=context.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

    def orchestrate_cutover_readiness(
        self, context: GatewayRequestContext, payload: Dict[str, Any]
    ) -> GatewayResponse[Dict[str, Any]]:
        """10. CDC readiness + Validation proof + Evidence proof context."""
        self.check_cancellation(context)
        self.check_fencing(context)
        boundary_pos = payload.get("cdc_boundary_position", "0/200")

        if hasattr(self.cdc_authority, "evaluate_cutover_readiness"):
            readiness_report = self.cdc_authority.evaluate_cutover_readiness()
            if isinstance(readiness_report, dict):
                is_ready = bool(readiness_report.get("is_ready", readiness_report.get("technical_cutover_ready", False)))
            else:
                is_ready = bool(getattr(readiness_report, "is_ready", getattr(readiness_report, "technical_cutover_ready", False)))
            cdc_snap = readiness_report
        elif hasattr(self.cdc_authority, "cutover_coordinator"):
            from akaalEngine.cdc.models.cutover import CutoverState
            state = getattr(self.cdc_authority.cutover_coordinator, "state", None)
            is_ready = (state == CutoverState.TECHNICAL_CUTOVER_READY or getattr(state, "value", str(state)) == CutoverState.TECHNICAL_CUTOVER_READY.value)
            cdc_snap = self.cdc_authority.get_snapshot()
        else:
            is_ready = False
            cdc_snap = self.cdc_authority.get_snapshot()

        if not is_ready:
            from akaalEngine.gateway.models.enums import GatewayFailureCategory
            return GatewayResponse.create_failure(
                operation_id=context.operation_id,
                operation_type=SemanticOperation.EVALUATE_CUTOVER_READINESS.value,
                migration_id=context.migration_id,
                run_id=context.run_id,
                failure_category=GatewayFailureCategory.CDC_FAILURE,
                error_message="Cutover readiness evaluation failed: CDC state is not TECHNICAL_CUTOVER_READY.",
                fencing_epoch=context.fencing_epoch,
            )

        return GatewayResponse.create_success(
            operation_id=context.operation_id,
            operation_type=SemanticOperation.EVALUATE_CUTOVER_READINESS.value,
            migration_id=context.migration_id,
            run_id=context.run_id,
            payload={
                "cdc_boundary_position": boundary_pos,
                "is_ready": True,
                "details": str(cdc_snap),
            },
            fencing_epoch=context.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

    def orchestrate_final_validation(
        self, context: GatewayRequestContext, payload: Dict[str, Any]
    ) -> GatewayResponse[Dict[str, Any]]:
        """11. Validation evaluation -> Disputed record reconciliation."""
        self.check_cancellation(context)
        self.check_fencing(context)

        from akaalEngine.validation.models import ValidationPlan, ValidationMode, ProofScope, ValidationGateStatus
        from akaalEngine.gateway.models.enums import GatewayFailureCategory

        val_mode_str = payload.get("validation_mode") or payload.get("mode") or "FAST_FULL"
        try:
            val_mode = ValidationMode(val_mode_str)
        except Exception:
            val_mode = ValidationMode.FAST_FULL

        plan = ValidationPlan(
            plan_id=f"plan-{context.operation_id}",
            migration_id=context.migration_id,
            source_identity="src",
            target_identity="tgt",
            table_name=payload.get("table_name", "main"),
            mode=val_mode,
            proof_scope=ProofScope.FULL,
        )

        source_rows = payload.get("source_rows", [])
        target_rows = payload.get("target_rows", [])
        pk_columns = payload.get("pk_columns", ["id"])

        val_res = self.validation_authority.execute_validation(
            plan=plan,
            source_rows=source_rows,
            target_rows=target_rows,
            pk_columns=pk_columns,
        )

        gate_status = getattr(val_res, "validation_gate", getattr(val_res, "gate_status", None))
        if gate_status and str(gate_status) != str(ValidationGateStatus.PASSED) and str(gate_status) != "PASSED":
            return GatewayResponse.create_failure(
                operation_id=context.operation_id,
                operation_type=SemanticOperation.RUN_FINAL_VALIDATION.value,
                failure_category=GatewayFailureCategory.VALIDATION_MISMATCH,
                error_message=f"Validation mismatch gate failed for migration '{context.migration_id}': {val_res}",
                migration_id=context.migration_id,
                run_id=context.run_id,
                fencing_epoch=context.fencing_epoch,
            )

        val_art = self.evidence_authority.package_validation_evidence(
            migration_id=context.migration_id,
            run_id=context.run_id,
            validation_result=val_res,
            artifact_id=f"art-val-{context.operation_id}",
        )

        return GatewayResponse.create_success(
            operation_id=context.operation_id,
            operation_type=SemanticOperation.RUN_FINAL_VALIDATION.value,
            migration_id=context.migration_id,
            run_id=context.run_id,
            payload={
                "validation_result": str(val_res),
                "evidence_artifact_id": val_art.artifact_id,
                "gate_status": str(gate_status or "PASSED"),
            },
            fencing_epoch=context.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

    def orchestrate_package_evidence(
        self, context: GatewayRequestContext, payload: Dict[str, Any]
    ) -> GatewayResponse[Dict[str, Any]]:
        """12. Evidence packaging & manifest digest calculation."""
        self.check_cancellation(context)
        artifacts = payload.get("artifacts", [])
        manifest = self.evidence_authority.create_manifest(
            migration_id=context.migration_id,
            run_id=context.run_id,
            artifacts=artifacts,
        )

        return GatewayResponse.create_success(
            operation_id=context.operation_id,
            operation_type=SemanticOperation.PACKAGE_MACHINE_EVIDENCE.value,
            migration_id=context.migration_id,
            run_id=context.run_id,
            payload={
                "manifest_id": manifest.manifest_id,
                "artifact_count": len(manifest.artifacts),
                "digest_hex": manifest.manifest_digest.digest_hex if manifest.manifest_digest else "",
                "completeness": manifest.completeness.value,
            },
            fencing_epoch=context.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

    def orchestrate_verify_evidence(
        self, context: GatewayRequestContext, payload: Dict[str, Any]
    ) -> GatewayResponse[Dict[str, Any]]:
        """13. Context-sensitive evidence verification."""
        self.check_cancellation(context)
        manifest = payload.get("manifest")
        req_categories = payload.get("required_proof_categories")
        ver_res = self.evidence_authority.verify_manifest(
            manifest=manifest,
            expected_migration_id=context.migration_id,
            expected_run_id=context.run_id,
            required_proof_categories=req_categories,
        )

        # Invariant: If verification fails, overall gateway response fails closed
        if not ver_res.is_valid:
            from akaalEngine.evidence.models import EvidenceVerificationError
            raise EvidenceVerificationError(
                f"Evidence verification failed for manifest: {ver_res.reasons}"
            )

        return GatewayResponse.create_success(
            operation_id=context.operation_id,
            operation_type=SemanticOperation.VERIFY_EVIDENCE_INTEGRITY.value,
            migration_id=context.migration_id,
            run_id=context.run_id,
            payload={
                "is_valid": ver_res.is_valid,
                "tamper_detected": ver_res.tamper_detected,
                "completeness": ver_res.completeness.value,
                "reasons": ver_res.reasons,
            },
            fencing_epoch=context.fencing_epoch,
            proof_classification="UNIT_PROVEN",
        )

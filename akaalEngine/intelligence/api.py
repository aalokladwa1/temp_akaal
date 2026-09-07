"""akaalEngine.intelligence.api
===============================
Single Canonical Entrypoint and Façade for the P7C.1 Intelligence Kernel.

Follows the exact "Authority façade" convention already established by
akaalEngine.telemetry.api.TelemetryAuthority (#7), akaalEngine.validation.api.
ValidationAuthority (#11), and akaalEngine.evidence.api.EvidenceAuthority (#12):
a single class other subsystems consume by injection, never a second competing
authority for anything it touches.

Permanent law: this kernel never grants its own authorization, never writes
Evidence/Validation truth, and never mutates canonical migration state. It produces
IntelligenceArtifact records that downstream canonical authorities (policy, approval,
planning) may choose to consume -- generation is not consequence.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional

from akaalEngine.intelligence.budget import (
    CancellationToken,
    RequestBudget,
    check_budget_and_cancellation,
)
from akaalEngine.intelligence.identity.fingerprint import (
    compute_artifact_fingerprint,
    compute_context_fingerprint,
    sha256_hex,
    canonical_json,
)
from akaalEngine.intelligence.evaluation import OutcomeRecord, OutcomeStore
from akaalEngine.intelligence.lifecycle.staleness import is_context_stale, is_expired
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.artifact import IntelligenceArtifact
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import (
    IntelligenceInvalidTransitionError,
    IntelligenceNotFoundError,
    IntelligenceTaskUnsupportedError,
    IntelligenceTenantBoundaryError,
    IntelligenceValidationError,
)
from akaalEngine.intelligence.models.lifecycle import ArtifactLifecycleState, validate_transition
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)

logger = logging.getLogger("akaalEngine.intelligence.api")

Producer = Callable[[IntelligenceRequest, IntelligenceContext], IntelligenceResult]


class IntelligenceKernel:
    """
    Single Canonical Façade for the P7C.1 Intelligence Kernel.
    Owns request/artifact contracts, deterministic identity/fingerprinting, the
    artifact lifecycle state machine, staleness evaluation, and cancellation/budget
    enforcement. Producers (deterministic, analytical, or generative computation --
    see P7C brief §7) are registered per IntelligenceTask; the kernel itself performs
    no analytical/generative computation of its own.
    """

    def __init__(
        self,
        store: Optional[IntelligenceArtifactStore] = None,
        telemetry_authority: Optional[Any] = None,
        evidence_authority: Optional[Any] = None,
        validation_authority: Optional[Any] = None,
        default_artifact_ttl_seconds: float = 3600.0,
    ) -> None:
        self.store = store or IntelligenceArtifactStore()
        self.outcome_store = OutcomeStore()
        self.telemetry_authority = telemetry_authority
        self.evidence_authority = evidence_authority
        self.validation_authority = validation_authority
        self.default_artifact_ttl_seconds = default_artifact_ttl_seconds
        self._producers: Dict[tuple, Producer] = {}
        self.register_producer(IntelligenceTask.QUERY, self._kernel_self_diagnostic_producer)

    # --- Producer registration -------------------------------------------------
    def register_producer(self, task: IntelligenceTask, producer: Producer, capability: Optional[str] = None) -> None:
        """Registers a producer for a (task, capability) pair. `capability` is an
        open string namespace (e.g. 'estate_assessment', 'wave_planning') so
        multiple distinct Campaign B producers can share the same coarse
        IntelligenceTask without colliding -- see IntelligenceRequest.capability."""
        self._producers[(task, capability)] = producer

    def has_producer(self, task: IntelligenceTask, capability: Optional[str] = None) -> bool:
        return (task, capability) in self._producers

    # --- Built-in deterministic P7C.1 producer ---------------------------------
    def _kernel_self_diagnostic_producer(
        self, request: IntelligenceRequest, context: IntelligenceContext
    ) -> IntelligenceResult:
        """The only producer P7C.1 itself ships: a genuinely computed (not
        fabricated) diagnostic over the request/context actually supplied. It
        proves the full request->artifact contract end-to-end without pretending
        real assessment/strategy/optimization intelligence (Campaign B, P7C.7+)
        already exists."""
        context_fp = compute_context_fingerprint(context)
        supporting = [
            f"tenant_id={context.tenant_id}",
            f"subject={context.subject_type}:{context.subject_id}@{context.subject_version}",
            f"context_fingerprint={context_fp}",
        ]
        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.FACT,
            summary=(
                f"Canonical context fingerprint computed for subject "
                f"{context.subject_type}:{context.subject_id}."
            ),
            explanation=Explanation(
                summary="Deterministic fingerprint of the supplied context dimensions.",
                supporting_facts=supporting,
            ),
            confidence_evidence=ConfidenceEvidence(evidence_coverage=1.0, source_freshness="current"),
            data={"context_fingerprint": context_fp},
        )

    # --- Submission --------------------------------------------------------
    def submit_request(
        self,
        request: IntelligenceRequest,
        context: IntelligenceContext,
        conn: sqlite3.Connection,
        *,
        cancellation_token: Optional[CancellationToken] = None,
        budget: Optional[RequestBudget] = None,
        supersede_previous: bool = False,
    ) -> IntelligenceArtifact:
        if request.tenant_id != context.tenant_id:
            raise IntelligenceTenantBoundaryError(
                f"IntelligenceRequest.tenant_id {request.tenant_id!r} does not match "
                f"IntelligenceContext.tenant_id {context.tenant_id!r}."
            )
        if request.subject_type != context.subject_type or request.subject_id != context.subject_id:
            raise IntelligenceValidationError(
                "IntelligenceRequest subject does not match IntelligenceContext subject."
            )

        producer = self._producers.get((request.task, request.capability))
        if producer is None:
            raise IntelligenceTaskUnsupportedError(
                f"No producer registered for task {request.task.value!r} "
                f"capability {request.capability!r}. Refusing to fabricate a result."
            )

        budget = budget or RequestBudget(max_seconds=request.timeout_seconds)
        check_budget_and_cancellation(budget, cancellation_token)

        result = producer(request, context)
        check_budget_and_cancellation(budget, cancellation_token)

        context_fp = compute_context_fingerprint(context)
        result_dict = result.to_dict()
        result_fp = sha256_hex(canonical_json(result_dict))
        artifact_fp = compute_artifact_fingerprint(
            context_fingerprint=context_fp,
            task=request.task.value,
            algorithm_version=request.algorithm_version,
            policy_version=request.policy_version,
            result_fingerprint=result_fp,
        )

        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=self.default_artifact_ttl_seconds)).isoformat()

        artifact = IntelligenceArtifact(
            artifact_id=IntelligenceArtifact.new_id(),
            tenant_id=context.tenant_id,
            workspace_id=context.workspace_id,
            project_id=context.project_id,
            subject_type=context.subject_type,
            subject_id=context.subject_id,
            subject_version=context.subject_version,
            task=request.task,
            algorithm_version=request.algorithm_version,
            policy_version=request.policy_version,
            canonical_state_fingerprint=context_fp,
            fingerprint=artifact_fp,
            result=result_dict,
            lifecycle_state=ArtifactLifecycleState.GENERATED,
            created_at=now.isoformat(),
            requested_by=request.requested_by,
            expires_at=expires_at,
        )
        self.store.save(artifact, conn)
        self._emit_telemetry("intelligence.artifact.generated", artifact)

        if supersede_previous:
            self._supersede_prior_artifacts(artifact, conn)

        return artifact

    def _supersede_prior_artifacts(self, new_artifact: IntelligenceArtifact, conn: sqlite3.Connection) -> None:
        """Marks any earlier non-terminal artifact for the same (tenant, subject,
        task) SUPERSEDED by the freshly generated one (P7C brief §P7C.1 'Expiry/
        supersession'). A superseded recommendation is never left ambiguously
        alongside its replacement -- exactly one artifact per (subject, task)
        remains in a non-terminal state after this call."""
        from akaalEngine.intelligence.models.lifecycle import is_terminal

        prior = self.store.list_by_tenant(
            new_artifact.tenant_id,
            conn,
            subject_id=new_artifact.subject_id,
            limit=500,
        )
        for candidate in prior:
            if candidate.artifact_id == new_artifact.artifact_id:
                continue
            if candidate.task != new_artifact.task:
                continue
            if is_terminal(candidate.lifecycle_state):
                continue
            self.transition(candidate.artifact_id, ArtifactLifecycleState.SUPERSEDED, conn, superseded_by=new_artifact.artifact_id)

    # --- Retrieval -----------------------------------------------------------
    def get_artifact(self, artifact_id: str, conn: sqlite3.Connection, *, verify_integrity: bool = False) -> IntelligenceArtifact:
        artifact = self.store.get(artifact_id, conn)
        if verify_integrity and not self.verify_artifact_integrity(artifact):
            from akaalEngine.intelligence.models.errors import IntelligenceValidationError

            raise IntelligenceValidationError(
                f"Artifact {artifact_id!r} failed integrity verification: stored fingerprint does not match "
                f"recomputation from its own (context, task, algorithm/policy version, result) fields. "
                f"Refusing to return a tampered-or-corrupted artifact for consequential use."
            )
        return artifact

    def verify_artifact_integrity(self, artifact: IntelligenceArtifact) -> bool:
        """Recomputes the artifact's fingerprint from its own stored fields and
        compares against the stored fingerprint (P7C brief §18 'modified
        fingerprint' hostile scenario). A row whose `result` content was altered
        at rest without correspondingly updating `fingerprint` fails this check."""
        result_fp = sha256_hex(canonical_json(dict(artifact.result)))
        recomputed = compute_artifact_fingerprint(
            context_fingerprint=artifact.canonical_state_fingerprint,
            task=artifact.task.value,
            algorithm_version=artifact.algorithm_version,
            policy_version=artifact.policy_version,
            result_fingerprint=result_fp,
            model_provider=artifact.model_provider or "",
            model_id=artifact.model_id or "",
            model_version=artifact.model_version or "",
        )
        return recomputed == artifact.fingerprint

    def list_artifacts(
        self,
        tenant_id: str,
        conn: sqlite3.Connection,
        *,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[IntelligenceArtifact]:
        return self.store.list_by_tenant(
            tenant_id,
            conn,
            workspace_id=workspace_id,
            project_id=project_id,
            subject_id=subject_id,
            limit=limit,
            offset=offset,
        )

    # --- Staleness & lifecycle transitions ------------------------------------
    def evaluate_staleness(self, artifact: IntelligenceArtifact, current_context: IntelligenceContext) -> bool:
        """Read-only staleness check -- does not mutate the artifact. Callers that
        need a persisted STALE transition should call `refresh_staleness` next."""
        return is_context_stale(artifact, current_context) or is_expired(artifact)

    def refresh_staleness(
        self, artifact: IntelligenceArtifact, current_context: IntelligenceContext, conn: sqlite3.Connection
    ) -> IntelligenceArtifact:
        """Evaluates staleness/expiry against current context and, if the artifact is
        not already in a terminal state, persists the appropriate transition. Must be
        called before any consequential re-use of a previously generated artifact."""
        from akaalEngine.intelligence.models.lifecycle import is_terminal

        if is_terminal(artifact.lifecycle_state):
            return artifact

        if is_expired(artifact):
            return self.transition(artifact.artifact_id, ArtifactLifecycleState.EXPIRED, conn)
        if is_context_stale(artifact, current_context):
            return self.transition(artifact.artifact_id, ArtifactLifecycleState.STALE, conn)
        return artifact

    def transition(
        self,
        artifact_id: str,
        to_state: ArtifactLifecycleState,
        conn: sqlite3.Connection,
        *,
        superseded_by: Optional[str] = None,
    ) -> IntelligenceArtifact:
        artifact = self.store.get(artifact_id, conn)
        validate_transition(artifact.lifecycle_state, to_state)
        updated = artifact.with_state(to_state, superseded_by=superseded_by)
        self.store.update_state(updated, conn)
        self._emit_telemetry(f"intelligence.artifact.{to_state.value.lower()}", updated)
        return updated

    # --- Outcome tracking (P7C brief §14 item 23) -----------------------------
    def record_outcome(
        self,
        *,
        artifact_id: str,
        tenant_id: str,
        outcome_status: str,
        conn: sqlite3.Connection,
        detail: str = "",
        metrics: Optional[Mapping[str, Any]] = None,
    ) -> OutcomeRecord:
        """Records what actually happened after an artifact's recommendation was
        acted on. Enforces tenant match against the artifact itself -- an
        outcome can never be recorded under a tenant the artifact doesn't
        belong to."""
        artifact = self.store.get(artifact_id, conn)
        if artifact.tenant_id != tenant_id:
            raise IntelligenceTenantBoundaryError(
                f"Cannot record outcome for artifact {artifact_id!r}: tenant mismatch "
                f"({tenant_id!r} != {artifact.tenant_id!r})."
            )
        outcome = OutcomeRecord.new(
            artifact_id=artifact_id, tenant_id=tenant_id, outcome_status=outcome_status, detail=detail, metrics=metrics
        )
        self.outcome_store.save(outcome, conn)
        return outcome

    def list_outcomes(self, artifact_id: str, conn: sqlite3.Connection) -> list:
        return self.outcome_store.list_for_artifact(artifact_id, conn)

    # --- Telemetry (redacted, never raises) -----------------------------------
    def _emit_telemetry(self, event_type: str, artifact: IntelligenceArtifact) -> None:
        if self.telemetry_authority is None:
            return
        try:
            if hasattr(self.telemetry_authority, "record_event"):
                self.telemetry_authority.record_event(
                    {
                        "event_type": event_type,
                        "producer_id": "akaalEngine.intelligence",
                        "tenant_id": artifact.tenant_id,
                        "task": artifact.task.value,
                        "artifact_id": artifact.artifact_id,
                        "lifecycle_state": artifact.lifecycle_state.value,
                    }
                )
        except Exception as exc:  # noqa: BLE001 -- telemetry must never fail a request
            logger.warning("[IntelligenceKernel] telemetry emission failed: %s", exc)

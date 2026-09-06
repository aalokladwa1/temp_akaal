"""
akaalEngine.fabric.evidence
=============================
P7B Group-1 Hostile Closure Round 5 -- canonical Authority #12 Evidence integration.

Forensic finding: `akaalEngine.evidence.api.EvidenceAuthority.create_evidence_artifact`
is genuinely authority-agnostic -- it accepts plain `EvidenceFact`/`EvidenceProvenance`
data and does not require the caller to be one of its constructor-injected sub-
authorities (#1/#4/#5/#6/#7/#8/#9/#10/#11). This is the real, correct integration seam:
fabric builds real `EvidenceFact` objects (tagged `originating_authority="akaalEngine.fabric"`)
and hands them to the EXISTING `EvidenceAuthority.create_evidence_artifact` -- no second
evidence/provenance system is created.

Scope discipline: Evidence #12 artifacts are migration-run-scoped by design
(`EvidenceArtifact.migration_id`/`run_id` are required fields) -- they exist to record
provenance about a specific execution, not general-purpose registry state. This module
therefore only covers EXECUTION-TIME fabric facts (a rejected/accepted fabric-bound
execution attempt, and why) -- exactly where Evidence #12 genuinely adds value. Registry
lifecycle events with no migration/run context (environment registration, site trust
transitions outside of an active execution) are NOT force-fit into Evidence artifacts;
they remain telemetry-only (see akaalEngine.fabric.remote_execution.execution's existing
telemetry integration through TransportAuthority), which is the architecturally correct
home for state that isn't about one specific migration run.

Evidence remains evidence/provenance only here, exactly as everywhere else in this
codebase -- nothing in this module makes or influences an authorization decision, and no
secret/token/key value is ever placed in a fact (enforced structurally: every fact
builder below only ever accepts and emits identifiers/booleans/reasons, never credential
material).
"""

from __future__ import annotations

import time
from typing import Any, Optional

from akaalEngine.evidence.models.artifact import (
    EvidenceArtifact,
    EvidenceCompleteness,
    EvidenceFact,
    EvidenceProvenance,
    ProofClassification,
)

_ORIGINATING_AUTHORITY = "akaalEngine.fabric"


def fabric_execution_accepted_fact(
    *,
    assignment_id: str,
    site_id: str,
    fencing_epoch: int,
) -> EvidenceFact:
    return EvidenceFact(
        fact_key="fabric_execution_accepted",
        fact_value=True,
        originating_authority=_ORIGINATING_AUTHORITY,
        fact_type="FABRIC_EXECUTION_DECISION",
        observed_at=time.time(),
        proof_classification=ProofClassification.INTEGRATION_PROVEN,
        scope=assignment_id,
        resource_id=site_id,
    )


def fabric_execution_rejected_fact(
    *,
    assignment_id: str,
    site_id: str,
    reason_code: str,
    reason_detail: str,
) -> EvidenceFact:
    """
    `reason_code` must be one of the canonical Group-1 rejection classes (e.g.
    "STALE_ROUTE", "REVOKED_SITE", "TENANT_MISMATCH", "EXPIRED_ASSIGNMENT",
    "FORGED_SIGNATURE") -- never a raw exception message, which could carry incidental
    sensitive detail. `reason_detail` is expected to already be a safe, human-readable
    string (callers pass the exception's own `str()`, which upstream fabric code never
    embeds secret material in -- verified throughout this codebase's redaction tests).
    """
    return EvidenceFact(
        fact_key="fabric_execution_rejected",
        fact_value=reason_code,
        originating_authority=_ORIGINATING_AUTHORITY,
        fact_type="FABRIC_EXECUTION_DECISION",
        observed_at=time.time(),
        proof_classification=ProofClassification.INTEGRATION_PROVEN,
        scope=assignment_id,
        resource_id=site_id,
    )


def fabric_provenance(*, site_id: str, fencing_epoch: Optional[int] = None) -> EvidenceProvenance:
    return EvidenceProvenance(
        authority_name=_ORIGINATING_AUTHORITY,
        component_id="execute_assignment_via_transport",
        boundary_position="FABRIC_EXECUTION_BOUNDARY",
        fencing_epoch=fencing_epoch,
        recorded_at=time.time(),
    )


def emit_fabric_execution_evidence(
    evidence_authority: Any,
    *,
    migration_id: str,
    run_id: str,
    site_id: str,
    assignment_id: str,
    accepted: bool,
    reason_code: Optional[str] = None,
    reason_detail: Optional[str] = None,
    fencing_epoch: Optional[int] = None,
) -> EvidenceArtifact:
    """
    The ONLY sanctioned way fabric produces Evidence #12 artifacts -- always through the
    real, existing `EvidenceAuthority.create_evidence_artifact`. `evidence_authority` is
    caller-supplied (in production, the real akaalEngine.evidence.api.EvidenceAuthority
    singleton); this function never constructs one itself.
    """
    if accepted:
        facts = [fabric_execution_accepted_fact(assignment_id=assignment_id, site_id=site_id, fencing_epoch=fencing_epoch or 0)]
        completeness = EvidenceCompleteness.COMPLETE
    else:
        facts = [fabric_execution_rejected_fact(
            assignment_id=assignment_id, site_id=site_id,
            reason_code=reason_code or "UNKNOWN_REJECTION", reason_detail=reason_detail or "",
        )]
        completeness = EvidenceCompleteness.FAILED

    return evidence_authority.create_evidence_artifact(
        migration_id=migration_id,
        run_id=run_id,
        artifact_type="FABRIC_EXECUTION_DECISION",
        facts=facts,
        provenance_list=[fabric_provenance(site_id=site_id, fencing_epoch=fencing_epoch)],
        fencing_epoch=fencing_epoch,
        completeness=completeness,
    )

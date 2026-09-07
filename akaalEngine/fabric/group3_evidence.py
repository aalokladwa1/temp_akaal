"""
akaalEngine.fabric.group3_evidence
======================================
P7B.34 -- Fabric Governance, Audit & Evidence Integration.

Mirrors akaalEngine.fabric.evidence's exact integration discipline (P7B Group-1) for the
Group-3 distributed-execution events it did not yet cover: ownership acquisition/renewal/
transfer/fencing, failover, and GitOps reconciliation. Builds real `EvidenceFact`/
`EvidenceProvenance` objects (tagged `originating_authority="akaalEngine.fabric.group3"`)
for callers to hand to the EXISTING `akaalEngine.evidence.api.EvidenceAuthority.
create_evidence_artifact` -- this module creates NO second evidence/provenance/audit
authority, and does not itself hold an EvidenceAuthority instance.

EVIDENCE != AUTHORIZATION (P7B Group-3 law): every fact builder below is a pure function
with no side effect on ownership/placement/failover state -- Evidence-store failure can
never authorize execution, convert failure into success, or hide a security rejection,
because nothing in the Group-3 decision path (SiteCoordinator, OwnershipManager,
attempt_failover, reconcile_fleet_state) reads evidence back to make a decision (proven
structurally in tests/unit/engine_fabric/test_p7b34_governance_evidence.py::
test_no_decision_module_imports_group3_evidence).

Secret redaction: every fact builder below accepts only identifiers/enum-strings/counts/
reasons as parameters -- there is no parameter anywhere in this module shaped to accept a
password, token, private key, or cloud credential (enforced structurally, same discipline
as akaalEngine.fabric.telemetry_integration).
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

_ORIGINATING_AUTHORITY = "akaalEngine.fabric.group3"


def ownership_acquired_fact(*, ownership_key: str, tenant_id: str, site_id: str, worker_id: str, fencing_generation: int) -> EvidenceFact:
    return EvidenceFact(
        fact_key="fabric_ownership_acquired", fact_value=True,
        originating_authority=_ORIGINATING_AUTHORITY, fact_type="FABRIC_OWNERSHIP_DECISION",
        observed_at=time.time(), proof_classification=ProofClassification.INTEGRATION_PROVEN,
        scope=ownership_key, resource_id=site_id,
    )


def ownership_renewed_fact(*, ownership_key: str, fencing_generation: int, site_id: str) -> EvidenceFact:
    return EvidenceFact(
        fact_key="fabric_ownership_renewed", fact_value=fencing_generation,
        originating_authority=_ORIGINATING_AUTHORITY, fact_type="FABRIC_OWNERSHIP_DECISION",
        observed_at=time.time(), proof_classification=ProofClassification.INTEGRATION_PROVEN,
        scope=ownership_key, resource_id=site_id,
    )


def ownership_transferred_fact(*, ownership_key: str, old_site_id: str, new_site_id: str, new_fencing_generation: int) -> EvidenceFact:
    return EvidenceFact(
        fact_key="fabric_ownership_transferred", fact_value={"from": old_site_id, "to": new_site_id},
        originating_authority=_ORIGINATING_AUTHORITY, fact_type="FABRIC_OWNERSHIP_DECISION",
        observed_at=time.time(), proof_classification=ProofClassification.INTEGRATION_PROVEN,
        scope=ownership_key, resource_id=new_site_id,
    )


def ownership_fenced_fact(*, ownership_key: str, site_id: str, reason: str) -> EvidenceFact:
    """`reason` must already be a safe, human-readable string (same discipline as
    akaalEngine.fabric.evidence.fabric_execution_rejected_fact's `reason_detail` --
    production callers pass an already-redacted reason, never raw exception text that
    might carry incidental sensitive detail)."""
    return EvidenceFact(
        fact_key="fabric_ownership_fenced", fact_value=reason,
        originating_authority=_ORIGINATING_AUTHORITY, fact_type="FABRIC_OWNERSHIP_DECISION",
        observed_at=time.time(), proof_classification=ProofClassification.INTEGRATION_PROVEN,
        scope=ownership_key, resource_id=site_id,
    )


def failover_decision_fact(*, ownership_key: str, outcome: str, old_site_id: Optional[str], new_site_id: Optional[str]) -> EvidenceFact:
    return EvidenceFact(
        fact_key="fabric_failover_decision", fact_value=outcome,
        originating_authority=_ORIGINATING_AUTHORITY, fact_type="FABRIC_FAILOVER_DECISION",
        observed_at=time.time(), proof_classification=ProofClassification.INTEGRATION_PROVEN,
        scope=ownership_key, resource_id=(new_site_id or old_site_id),
    )


def gitops_reconciliation_fact(*, revision_id: str, state: str, active_worker_count: int) -> EvidenceFact:
    return EvidenceFact(
        fact_key="fabric_gitops_reconciliation", fact_value=state,
        originating_authority=_ORIGINATING_AUTHORITY, fact_type="FABRIC_GITOPS_DECISION",
        observed_at=time.time(), proof_classification=ProofClassification.INTEGRATION_PROVEN,
        scope=revision_id, resource_id=None,
    )


def group3_provenance(*, site_id: str, fencing_generation: Optional[int] = None, component_id: str = "fabric.group3") -> EvidenceProvenance:
    return EvidenceProvenance(
        authority_name=_ORIGINATING_AUTHORITY, component_id=component_id,
        boundary_position="FABRIC_DISTRIBUTED_EXECUTION_BOUNDARY",
        fencing_epoch=fencing_generation, recorded_at=time.time(),
    )


def emit_ownership_decision_evidence(
    evidence_authority: Any,
    *,
    migration_id: str,
    run_id: str,
    ownership_key: str,
    tenant_id: str,
    site_id: str,
    worker_id: str,
    accepted: bool,
    event_type: str = "acquired",
    fencing_generation: Optional[int] = None,
    reason: Optional[str] = None,
) -> EvidenceArtifact:
    """
    THE only sanctioned way Group-3 ownership decisions produce Evidence #12 artifacts --
    mirrors akaalEngine.fabric.evidence.emit_fabric_execution_evidence's exact discipline
    (same real, unmodified `EvidenceAuthority.create_evidence_artifact`, never a second
    evidence authority). `evidence_authority` is caller-supplied and never constructed
    here. `event_type` is one of "acquired"/"renewed"/"fenced"/"rejected"/"released".

    EVIDENCE IS NEVER A GATE: this function's caller (execute_via_placement) is required
    to call this ONLY after the real ownership decision has already been made -- calling
    it, or its failure, never changes what already happened.
    """
    if accepted:
        facts = [ownership_acquired_fact(
            ownership_key=ownership_key, tenant_id=tenant_id, site_id=site_id, worker_id=worker_id,
            fencing_generation=fencing_generation or 0,
        )] if event_type == "acquired" else [ownership_renewed_fact(
            ownership_key=ownership_key, fencing_generation=fencing_generation or 0, site_id=site_id,
        )]
        completeness = EvidenceCompleteness.COMPLETE
    else:
        facts = [ownership_fenced_fact(ownership_key=ownership_key, site_id=site_id, reason=reason or "ownership rejected")]
        completeness = EvidenceCompleteness.FAILED

    return evidence_authority.create_evidence_artifact(
        migration_id=migration_id,
        run_id=run_id,
        artifact_type="FABRIC_OWNERSHIP_DECISION",
        facts=facts,
        provenance_list=[group3_provenance(site_id=site_id, fencing_generation=fencing_generation)],
        fencing_epoch=fencing_generation,
        completeness=completeness,
    )

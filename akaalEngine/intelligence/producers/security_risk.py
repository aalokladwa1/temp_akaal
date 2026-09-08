"""akaalEngine.intelligence.producers.security_risk
======================================================
P7C.19 -- Security, Compliance & Risk Intelligence. Classifies ALREADY-
COMPUTED canonical-derived facts from P7C.13 (FABRIC/VALIDATION), P7C.18
(pending governed remediation) into the risk-dimension taxonomy. Never a
second security/policy authority, never an invented compliance rule: a risk
this module cannot map to a genuine canonical fact is not reported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    DiagnosticFinding,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)


@dataclass(frozen=True)
class SecurityRiskInputs:
    tenant_id: str
    migration_id: str
    fabric_status: str = "UNKNOWN"
    validation_status: str = "UNKNOWN"
    pending_remediation_action_type: Optional[str] = None  # from P7C.18's own output, if any


SecurityRiskResolver = Callable[[IntelligenceRequest, IntelligenceContext], SecurityRiskInputs]


def make_security_risk_producer(resolver: SecurityRiskResolver):
    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        inputs = resolver(request, context)
        if inputs is None:
            raise IntelligenceValidationError(
                "Security risk resolver returned no SecurityRiskInputs. Refusing to fabricate "
                "a risk assessment with no canonical facts."
            )

        findings = []
        risk_dimensions = set()

        if inputs.fabric_status == "CRITICAL":
            findings.append(
                DiagnosticFinding(
                    code="RISK:FABRIC_OWNERSHIP_CRITICAL",
                    severity="HIGH",
                    message="Canonical P7B Fabric ownership is CRITICAL (expired lease, stale owner, or "
                    "fencing conflict) -- a genuine security/residency risk until resolved.",
                    evidence_refs=["FABRIC"],
                )
            )
            risk_dimensions.update({"SECURITY", "RESIDENCY", "OPERATIONAL"})

        if inputs.validation_status == "CRITICAL":
            findings.append(
                DiagnosticFinding(
                    code="RISK:VALIDATION_CRITICAL",
                    severity="HIGH",
                    message="Canonical Validation #11 reports a critical/failed state -- a data-integrity/"
                    "compliance risk until resolved. This module relays, never re-derives, that verdict.",
                    evidence_refs=["VALIDATION"],
                )
            )
            risk_dimensions.update({"DATA", "COMPLIANCE"})

        if inputs.pending_remediation_action_type:
            findings.append(
                DiagnosticFinding(
                    code="RISK:PENDING_GOVERNED_ACTION",
                    severity="MEDIUM",
                    message=f"A governed remediation proposal ({inputs.pending_remediation_action_type!r}) is "
                    "awaiting approval -- an operational risk window exists until it is actioned or dismissed.",
                    evidence_refs=["P7C.18"],
                )
            )
            risk_dimensions.add("OPERATIONAL")

        if findings:
            summary = f"{len(findings)} risk finding(s) for migration {inputs.migration_id!r} across dimensions: {sorted(risk_dimensions)}."
        else:
            summary = f"No elevated security/compliance/risk signals for migration {inputs.migration_id!r} from currently available canonical facts."

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.DIAGNOSIS,
            summary=summary,
            explanation=Explanation(
                summary="Risk classification derived entirely from already-computed canonical-derived facts "
                "(P7C.13 FABRIC/VALIDATION, P7C.18 pending proposals) -- never an invented compliance rule or "
                "fabricated control mapping. A risk this module cannot map to a genuine canonical fact is not reported.",
                supporting_facts=[f"fabric_status={inputs.fabric_status}", f"validation_status={inputs.validation_status}"],
            ),
            confidence_evidence=ConfidenceEvidence(evidence_coverage=1.0),
            findings=findings,
            data={
                "migration_id": inputs.migration_id,
                "risk_dimensions": sorted(risk_dimensions),
                "finding_count": len(findings),
            },
        )

    return producer

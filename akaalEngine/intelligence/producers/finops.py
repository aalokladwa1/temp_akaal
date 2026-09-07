"""akaalEngine.intelligence.producers.finops
================================================
P7C.20 -- FinOps, Resource & Sustainability Intelligence.

Owner-review Blocker 10 closure: forensic inspection of akaalPipeline found
NO canonical, versioned, organization-approved cost-configuration authority
in this repository today (verified: no cost/pricing table, no provider-rate
authority). Every `cost_per_worker_hour` this producer ever sees is
therefore, honestly and unavoidably, a CALLER-SUPPLIED ASSUMPTION for a
what-if scenario -- never authoritative organizational spend. This module
never blurs that distinction: every cost number it emits carries an explicit
`cost_source` provenance tag, currently ALWAYS "CALLER_SUPPLIED_ASSUMPTION".
If a real canonical cost-configuration authority is added to the repository
in the future, this module (and only this module) would need to be extended
with a "CANONICAL_CONFIGURED" tier sourced from it -- it must never be
fabricated ahead of that authority actually existing.

Cost math itself combines that caller-supplied rate with the REAL canonical
migration ETA already computed by P7C.17 (never re-derived here).
dataset_size_bytes/worker_count are the caller's own PLANNING inputs for a
"what-if" cost projection (the same class of legitimate caller-supplied
parameter P7C.12/P7C.16 already accept) -- never a claim about observed
operational health, which P7C.13's correction specifically forbids.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    EpistemicType,
    Explanation,
    IntelligenceResult,
    Prediction,
)

BYTES_PER_GB = 1_000_000_000

# The only cost-source classification this repository can honestly produce
# today (see module docstring). Kept as an explicit constant rather than a
# richer enum so a future "CANONICAL_CONFIGURED" tier is an obviously
# deliberate addition, never an accidental default.
COST_SOURCE_CALLER_ASSUMPTION = "CALLER_SUPPLIED_ASSUMPTION"

# Owner-review Blocker 11 closure: forensic inspection (grep across
# akaalPipeline for carbon/sustainability/co2/emission) found NO canonical,
# versioned sustainability/carbon-intensity data source anywhere in this
# repository. Rather than silently omitting the capability (which reads as
# "not asked" rather than "not answerable") or fabricating a number, P7C.20
# explicitly reports this status on every response -- a truthful capability
# boundary, not a missing feature.
SUSTAINABILITY_STATUS_NOT_CURRENTLY_PROVABLE = "NOT_CURRENTLY_PROVABLE"
SUSTAINABILITY_UNAVAILABLE_REASON = (
    "No canonical, versioned sustainability/carbon-intensity/energy-efficiency data source exists in this "
    "repository today (verified by inspection). Returning a carbon/sustainability estimate would require "
    "fabricating a number this codebase has no authoritative basis for -- refused rather than invented."
)


@dataclass(frozen=True)
class FinOpsInputs:
    tenant_id: str
    migration_id: str
    migration_eta_seconds: Optional[float] = None  # REAL canonical forecast (P7C.17), never caller-supplied
    dataset_size_bytes: Optional[float] = None  # caller planning input (scenario assumption)
    worker_count: Optional[int] = None  # caller planning input (scenario assumption)
    cost_per_worker_hour: Optional[float] = None  # caller-supplied rate -- NOT canonical org spend (see docstring)


FinOpsResolver = Callable[[IntelligenceRequest, IntelligenceContext], FinOpsInputs]


def make_finops_producer(resolver: FinOpsResolver):
    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        inputs = resolver(request, context)
        if inputs is None:
            raise IntelligenceValidationError(
                "FinOps resolver returned no FinOpsInputs. Refusing to fabricate a cost "
                "projection with no canonical/organization-configured facts."
            )

        predictions = []
        missing = []
        cost_to_completion = None

        if inputs.cost_per_worker_hour is None:
            missing.append("cost_per_worker_hour not supplied -- no invented price catalog is used, so cost is UNKNOWN.")
        if inputs.worker_count is None:
            missing.append("worker_count not supplied.")
        if inputs.migration_eta_seconds is None:
            missing.append("No canonical migration ETA is currently available (see P7C.17) -- cost-to-completion cannot be projected.")

        if inputs.cost_per_worker_hour is not None and inputs.worker_count is not None and inputs.migration_eta_seconds is not None:
            eta_hours = inputs.migration_eta_seconds / 3600.0
            cost_to_completion = inputs.cost_per_worker_hour * inputs.worker_count * eta_hours
            predictions.append(
                Prediction(
                    metric="cost_to_completion", value=cost_to_completion, unit="currency_unit",
                    basis=f"caller-supplied cost_per_worker_hour ({COST_SOURCE_CALLER_ASSUMPTION}) x worker_count "
                    "x canonical ETA hours (P7C.17) -- a what-if scenario estimate, not authoritative spend.",
                )
            )

        cost_per_gb = None
        if cost_to_completion is not None and inputs.dataset_size_bytes and inputs.dataset_size_bytes > 0:
            cost_per_gb = cost_to_completion / (inputs.dataset_size_bytes / BYTES_PER_GB)
            predictions.append(Prediction(metric="cost_per_gb", value=cost_per_gb, unit="currency_unit/GB", basis="cost_to_completion / dataset_size_gb (same assumption provenance)."))
        elif cost_to_completion is not None:
            missing.append("dataset_size_bytes not supplied -- cost_per_gb omitted.")

        status = "COST_PROJECTION_AVAILABLE" if cost_to_completion is not None else "UNKNOWN"
        summary = (
            f"FinOps SCENARIO projection for migration {inputs.migration_id!r}: {status} "
            f"(cost_source={COST_SOURCE_CALLER_ASSUMPTION} -- never authoritative organizational spend)."
        )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.PREDICTION if cost_to_completion is not None else EpistemicType.ASSUMPTION,
            summary=summary,
            explanation=Explanation(
                summary="Cost is derived only from a CALLER-SUPPLIED rate (this repository has no canonical, "
                "versioned cost-configuration authority today -- verified by inspection) and the real canonical "
                "ETA -- never an invented price catalog, never presented as authoritative organizational spend, "
                "never a fabricated projection when either input is missing.",
                supporting_facts=[f"cost_to_completion_status={status}", f"cost_source={COST_SOURCE_CALLER_ASSUMPTION}"],
                assumptions=(
                    [f"cost_per_worker_hour={inputs.cost_per_worker_hour!r} is a caller-supplied scenario assumption, not canonical organizational pricing."]
                    if inputs.cost_per_worker_hour is not None else []
                ),
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=1.0 if cost_to_completion is not None else 0.0,
                missing_information=missing,
            ),
            predictions=predictions,
            data={
                "migration_id": inputs.migration_id,
                "cost_status": status,
                "cost_source": COST_SOURCE_CALLER_ASSUMPTION,
                "cost_to_completion": cost_to_completion,
                "cost_per_gb": cost_per_gb,
                "sustainability": {
                    "status": SUSTAINABILITY_STATUS_NOT_CURRENTLY_PROVABLE,
                    "reason": SUSTAINABILITY_UNAVAILABLE_REASON,
                },
            },
        )

    return producer

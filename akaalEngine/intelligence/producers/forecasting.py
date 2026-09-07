"""akaalEngine.intelligence.producers.forecasting
====================================================
P7C.17 -- Predictive Operations & Forecasting. Reuses the P7C.12 duration/
feasibility arithmetic (akaalEngine.intelligence.producers.capacity_simulation
-- "no duplicate prediction authorities") applied to REAL canonical facts
(TelemetryAuthority.get_progress_snapshot's rows_remaining/rows_per_second)
rather than caller-supplied static rates.

CDC catch-up ETA is honestly reported as unavailable, not fabricated: P7C.13's
own correction established that true per-second CDC generation/apply rates
are not canonically exposed today (only mislabeled cumulative totals) -- this
module never treats those cumulative fields as rates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    DiagnosticFinding,
    EpistemicType,
    Explanation,
    IntelligenceResult,
    Prediction,
)
from akaalEngine.intelligence.producers.capacity_simulation import _range, estimate_cdc_catchup_seconds


@dataclass(frozen=True)
class ForecastInputs:
    """Bundled, already-resolved canonical facts -- zero discovery here."""

    migration_id: str
    rows_processed: Optional[int] = None
    rows_total: Optional[int] = None  # None or <= 0 means canonically unknown
    rows_per_second: Optional[float] = None
    cdc_backlog_bytes: Optional[float] = None
    cdc_generation_rate_bytes_per_sec: Optional[float] = None  # NOT_CURRENTLY_EXPOSED in this repository today
    cdc_apply_rate_bytes_per_sec: Optional[float] = None  # NOT_CURRENTLY_EXPOSED in this repository today
    fabric_status: str = "UNKNOWN"
    validation_status: str = "UNKNOWN"


ForecastResolver = Callable[[IntelligenceRequest, IntelligenceContext], ForecastInputs]


def make_forecast_producer(resolver: ForecastResolver):
    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        inputs = resolver(request, context)
        if inputs is None:
            raise IntelligenceValidationError(
                "Forecast resolver returned no ForecastInputs. Refusing to fabricate a "
                "forecast with no canonical facts."
            )

        predictions = []
        supporting_facts = []
        missing_information = []

        eta_status = "UNKNOWN"
        if (
            inputs.rows_total is not None and inputs.rows_total > 0
            and inputs.rows_processed is not None
            and inputs.rows_per_second is not None and inputs.rows_per_second > 0
        ):
            remaining = max(inputs.rows_total - inputs.rows_processed, 0)
            eta_seconds = remaining / inputs.rows_per_second
            low, point, high = _range(eta_seconds)
            predictions.append(
                Prediction(
                    metric="migration_eta_seconds", value=point, unit="seconds", low=low, high=high,
                    basis="rows_remaining / current canonical rows_per_second (TelemetryAuthority progress "
                    "tracker), +/-20% uncertainty band -- not a guarantee.",
                )
            )
            supporting_facts.append(f"rows_remaining={remaining}, rows_per_second={inputs.rows_per_second:.2f}")
            eta_status = "FORECAST_AVAILABLE"
        else:
            missing_information.append(
                "migration ETA requires canonical rows_total, rows_processed, and a positive rows_per_second; "
                "at least one was unavailable or the total is not yet known."
            )

        catchup_status = "UNKNOWN_RATES_NOT_CANONICALLY_AVAILABLE"
        if (
            inputs.cdc_backlog_bytes is not None
            and inputs.cdc_generation_rate_bytes_per_sec is not None
            and inputs.cdc_apply_rate_bytes_per_sec is not None
        ):
            catchup = estimate_cdc_catchup_seconds(
                inputs.cdc_backlog_bytes, inputs.cdc_generation_rate_bytes_per_sec, inputs.cdc_apply_rate_bytes_per_sec
            )
            if catchup is None:
                catchup_status = "NO_CATCHUP_ETA_NON_CONVERGENT"
                supporting_facts.append(
                    "CDC apply rate does not exceed generation rate -- backlog cannot mathematically converge."
                )
            else:
                low, point, high = catchup
                predictions.append(
                    Prediction(
                        metric="cdc_catchup_eta_seconds", value=point, unit="seconds", low=low, high=high,
                        basis="backlog / (apply_rate - generation_rate).",
                    )
                )
                catchup_status = "FORECAST_AVAILABLE"
        else:
            missing_information.append(
                "CDC catch-up ETA requires true per-second generation/apply rates, which are not canonically "
                "exposed today (only cumulative lifetime totals are available) -- reported as UNKNOWN, never derived "
                "from those mislabeled fields."
            )

        governance_critical = inputs.fabric_status == "CRITICAL" or inputs.validation_status == "CRITICAL"
        findings = []
        contradictions = []
        if governance_critical:
            contradictions.append(
                f"FABRIC={inputs.fabric_status!r}/VALIDATION={inputs.validation_status!r} is CRITICAL -- any "
                "duration forecast is unreliable until canonical governance state is resolved."
            )
            findings.append(
                DiagnosticFinding(
                    code="FORECAST:GOVERNANCE_CRITICAL",
                    severity="HIGH",
                    message="Canonical FABRIC/VALIDATION CRITICAL undermines any performance-based forecast.",
                    evidence_refs=["FABRIC", "VALIDATION"],
                )
            )

        available_count = sum(1 for s in (eta_status, catchup_status) if s == "FORECAST_AVAILABLE")
        evidence_coverage = available_count / 2.0

        summary = (
            f"Forecast for migration {inputs.migration_id!r}: migration_eta={eta_status}, "
            f"cdc_catchup={catchup_status}."
        )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.PREDICTION,
            summary=summary,
            explanation=Explanation(
                summary="Deterministic queueing arithmetic over canonical progress-tracker facts; never "
                "fabricates an ETA when a required canonical input is unavailable or the trend is non-convergent.",
                supporting_facts=supporting_facts,
                contradictions=contradictions,
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=evidence_coverage,
                missing_information=missing_information,
            ),
            findings=findings,
            predictions=predictions,
            data={
                "migration_id": inputs.migration_id,
                "migration_eta_status": eta_status,
                "cdc_catchup_status": catchup_status,
                "governance_critical": governance_critical,
            },
        )

    return producer

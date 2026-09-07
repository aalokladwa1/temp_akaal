"""akaalEngine.intelligence.producers.forecast_evaluation
============================================================
P7C.23 -- Evaluation, Feedback & Intelligence Operations (forecast task
specifically). Operationalizes Group-1's evaluation foundation
(akaalEngine.intelligence.evaluation.EvaluationResult) with a genuine,
deterministic metric: given a previously-issued P7C.17 prediction (median +
interval, supplied by the caller from that earlier response -- never
re-fetched/re-derived) and a later actual observed value, computes real
error/interval-hit metrics. Feedback != truth: this module only ever compares
two numbers the caller already has; it never asserts what "actually"
happened beyond the number supplied.
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
)


@dataclass(frozen=True)
class ForecastEvaluationInputs:
    metric_name: str
    predicted_value: float
    predicted_low: float
    predicted_high: float
    actual_value: float
    # Traceability to the EXACT P7C.17 IntelligenceArtifact this prediction
    # came from (owner-review Blocker 14). Optional for callers who only have
    # the raw numbers, but when supplied it is carried through into this
    # evaluation's own artifact `data`, so a later query can walk
    # evaluation-artifact -> forecast_artifact_id -> the original,
    # IMMUTABLE forecast artifact (akaalEngine.intelligence.lifecycle.store.
    # IntelligenceArtifactStore.save is INSERT-only; `result` is never
    # overwritten by a later forecast -- a new forecast always gets its own
    # new artifact_id, never mutates an old one).
    forecast_artifact_id: Optional[str] = None


ForecastEvaluationResolver = Callable[[IntelligenceRequest, IntelligenceContext], Optional[ForecastEvaluationInputs]]


def evaluate_forecast(inputs: ForecastEvaluationInputs) -> dict:
    """Pure, deterministic. No I/O."""
    error = inputs.actual_value - inputs.predicted_value
    abs_error = abs(error)
    relative_error = (abs_error / abs(inputs.predicted_value)) if inputs.predicted_value else None
    interval_hit = inputs.predicted_low <= inputs.actual_value <= inputs.predicted_high
    return {
        "metric_name": inputs.metric_name,
        "predicted_value": inputs.predicted_value,
        "actual_value": inputs.actual_value,
        "error": error,
        "abs_error": abs_error,
        "relative_error": relative_error,
        "interval_hit": interval_hit,
        "forecast_artifact_id": inputs.forecast_artifact_id,
    }


def make_forecast_evaluation_producer():
    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        params = request.parameters
        required = ["metric_name", "predicted_value", "predicted_low", "predicted_high", "actual_value"]
        missing = [k for k in required if k not in params]
        if missing:
            raise IntelligenceValidationError(f"Forecast evaluation missing required parameters: {missing}.")

        inputs = ForecastEvaluationInputs(
            metric_name=str(params["metric_name"]),
            predicted_value=float(params["predicted_value"]),
            predicted_low=float(params["predicted_low"]),
            predicted_high=float(params["predicted_high"]),
            actual_value=float(params["actual_value"]),
            forecast_artifact_id=params.get("forecast_artifact_id"),
        )
        result = evaluate_forecast(inputs)

        findings = []
        if not result["interval_hit"]:
            findings.append(
                DiagnosticFinding(
                    code="EVAL:INTERVAL_MISS",
                    severity="MEDIUM",
                    message=f"Actual value {inputs.actual_value} fell outside the predicted interval "
                    f"[{inputs.predicted_low}, {inputs.predicted_high}] -- the forecast's uncertainty band "
                    f"under-covered this outcome.",
                    evidence_refs=[inputs.metric_name],
                )
            )

        summary = (
            f"Forecast evaluation for {inputs.metric_name!r}: error={result['error']:.3g}, "
            f"interval_hit={result['interval_hit']}."
        )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.DERIVED_FACT,
            summary=summary,
            explanation=Explanation(
                summary="Deterministic comparison of a previously-issued prediction against a caller-supplied "
                "actual value -- feedback is not treated as canonical ground truth beyond the number supplied.",
                supporting_facts=[f"predicted={inputs.predicted_value}", f"actual={inputs.actual_value}"],
            ),
            confidence_evidence=ConfidenceEvidence(evidence_coverage=1.0),
            findings=findings,
            data=result,
        )

    return producer

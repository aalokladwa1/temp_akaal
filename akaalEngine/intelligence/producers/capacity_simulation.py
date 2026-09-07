"""akaalEngine.intelligence.producers.capacity_simulation
===========================================================
P7C.12 -- Capacity, Cutover, Scheduling & Scenario Simulation. Real, deterministic
queueing/throughput arithmetic -- no guaranteed ETA is ever produced (P7C brief
"Prediction honesty"); every estimate carries an explicit low/high range around a
point estimate, and CDC backlogs that mathematically never converge are reported
as infeasible rather than given a fabricated finish time.

Shared by P7C.8/.9/.12 conceptually (P7C brief "no duplicate prediction
authorities") -- this module owns the canonical duration/feasibility math; other
producers that need duration estimates should call into it rather than
inventing a second estimator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    EpistemicType,
    Explanation,
    IntelligenceResult,
    OptimizationAlternative,
    OptimizationResult,
    Prediction,
)

DEFAULT_UNCERTAINTY_PCT = 0.2


def _range(point: float, uncertainty_pct: float = DEFAULT_UNCERTAINTY_PCT) -> Tuple[float, float, float]:
    low = point * (1.0 - uncertainty_pct)
    high = point * (1.0 + uncertainty_pct)
    return (low, point, high)


def estimate_bulk_duration_seconds(
    dataset_size_bytes: float, worker_throughput_bytes_per_sec: float, worker_count: int
) -> Tuple[float, float, float]:
    if worker_throughput_bytes_per_sec <= 0 or worker_count <= 0:
        raise IntelligenceValidationError("worker_throughput_bytes_per_sec and worker_count must be positive.")
    effective_throughput = worker_throughput_bytes_per_sec * worker_count
    point = dataset_size_bytes / effective_throughput
    return _range(point)


def estimate_cdc_catchup_seconds(
    backlog_bytes: float, generation_rate_bytes_per_sec: float, apply_rate_bytes_per_sec: float
) -> Optional[Tuple[float, float, float]]:
    """Returns None (mathematically infeasible -- backlog grows without bound)
    when the apply rate does not exceed the generation rate. Never fabricates a
    finish time for a backlog that cannot converge."""
    net_rate = apply_rate_bytes_per_sec - generation_rate_bytes_per_sec
    if net_rate <= 0:
        return None
    point = backlog_bytes / net_rate
    return _range(point)


def estimate_validation_duration_seconds(dataset_size_bytes: float, validation_throughput_bytes_per_sec: float) -> Tuple[float, float, float]:
    if validation_throughput_bytes_per_sec <= 0:
        raise IntelligenceValidationError("validation_throughput_bytes_per_sec must be positive.")
    point = dataset_size_bytes / validation_throughput_bytes_per_sec
    return _range(point)


@dataclass(frozen=True)
class CutoverScenario:
    label: str
    worker_count: int
    bulk_duration: Tuple[float, float, float]
    cdc_catchup_duration: Optional[Tuple[float, float, float]]
    validation_duration: Tuple[float, float, float]
    cutover_window_seconds: float

    @property
    def total_point_seconds(self) -> Optional[float]:
        if self.cdc_catchup_duration is None:
            return None
        return self.bulk_duration[1] + self.cdc_catchup_duration[1] + self.validation_duration[1]

    @property
    def is_feasible(self) -> bool:
        total = self.total_point_seconds
        return total is not None and total <= self.cutover_window_seconds

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "worker_count": self.worker_count,
            "bulk_duration_seconds": {"low": self.bulk_duration[0], "point": self.bulk_duration[1], "high": self.bulk_duration[2]},
            "cdc_catchup_duration_seconds": (
                {"low": self.cdc_catchup_duration[0], "point": self.cdc_catchup_duration[1], "high": self.cdc_catchup_duration[2]}
                if self.cdc_catchup_duration is not None else None
            ),
            "validation_duration_seconds": {"low": self.validation_duration[0], "point": self.validation_duration[1], "high": self.validation_duration[2]},
            "cutover_window_seconds": self.cutover_window_seconds,
            "total_point_seconds": self.total_point_seconds,
            "is_feasible": self.is_feasible,
            "backlog_never_converges": self.cdc_catchup_duration is None,
        }


def evaluate_scenario(
    *,
    label: str,
    dataset_size_bytes: float,
    worker_throughput_bytes_per_sec: float,
    worker_count: int,
    validation_throughput_bytes_per_sec: float,
    cutover_window_seconds: float,
    cdc_backlog_bytes: float = 0.0,
    cdc_generation_rate_bytes_per_sec: float = 0.0,
    cdc_apply_rate_bytes_per_sec: float = 0.0,
) -> CutoverScenario:
    bulk = estimate_bulk_duration_seconds(dataset_size_bytes, worker_throughput_bytes_per_sec, worker_count)
    validation = estimate_validation_duration_seconds(dataset_size_bytes, validation_throughput_bytes_per_sec)
    cdc = None
    if cdc_backlog_bytes > 0 or cdc_generation_rate_bytes_per_sec > 0:
        cdc = estimate_cdc_catchup_seconds(cdc_backlog_bytes, cdc_generation_rate_bytes_per_sec, cdc_apply_rate_bytes_per_sec)
    else:
        cdc = (0.0, 0.0, 0.0)
    return CutoverScenario(
        label=label,
        worker_count=worker_count,
        bulk_duration=bulk,
        cdc_catchup_duration=cdc,
        validation_duration=validation,
        cutover_window_seconds=cutover_window_seconds,
    )


def make_capacity_simulation_producer():
    """IntelligenceKernel-compatible producer for IntelligenceTask.SIMULATE.

    request.parameters:
      - dataset_size_bytes, worker_throughput_bytes_per_sec, validation_throughput_bytes_per_sec,
        cutover_window_seconds: required floats.
      - worker_counts: list[int] -- one CutoverScenario evaluated per value ("what-if" comparison).
      - cdc_backlog_bytes, cdc_generation_rate_bytes_per_sec, cdc_apply_rate_bytes_per_sec: optional.
    """

    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        params = request.parameters
        required = ["dataset_size_bytes", "worker_throughput_bytes_per_sec", "validation_throughput_bytes_per_sec", "cutover_window_seconds"]
        missing = [k for k in required if k not in params]
        if missing:
            raise IntelligenceValidationError(f"Capacity simulation missing required parameters: {missing}.")

        worker_counts: List[int] = list(params.get("worker_counts") or [8])

        scenarios = [
            evaluate_scenario(
                label=f"{wc}_workers",
                dataset_size_bytes=float(params["dataset_size_bytes"]),
                worker_throughput_bytes_per_sec=float(params["worker_throughput_bytes_per_sec"]),
                worker_count=int(wc),
                validation_throughput_bytes_per_sec=float(params["validation_throughput_bytes_per_sec"]),
                cutover_window_seconds=float(params["cutover_window_seconds"]),
                cdc_backlog_bytes=float(params.get("cdc_backlog_bytes", 0.0)),
                cdc_generation_rate_bytes_per_sec=float(params.get("cdc_generation_rate_bytes_per_sec", 0.0)),
                cdc_apply_rate_bytes_per_sec=float(params.get("cdc_apply_rate_bytes_per_sec", 0.0)),
            )
            for wc in worker_counts
        ]

        feasible_scenarios = [s for s in scenarios if s.is_feasible]
        infeasible_backlog = [s for s in scenarios if s.cdc_catchup_duration is None]

        predictions = [
            Prediction(
                metric=f"total_duration_seconds[{s.label}]",
                value=s.total_point_seconds,
                unit="seconds",
                low=s.bulk_duration[0] + s.cdc_catchup_duration[0] + s.validation_duration[0],
                high=s.bulk_duration[2] + s.cdc_catchup_duration[2] + s.validation_duration[2],
                basis="deterministic throughput arithmetic with ±20% uncertainty band",
            )
            for s in scenarios if s.cdc_catchup_duration is not None
        ]

        alternatives = [
            OptimizationAlternative(
                label=s.label,
                # objective_scores values must stay JSON/fingerprint-safe finite
                # numbers -- a never-converging backlog has no finite duration to
                # report, so it is represented by "feasible": 0.0 alone rather
                # than an invented float("inf")/NaN stand-in value.
                objective_scores=(
                    {"feasible": 1.0 if s.is_feasible else 0.0, "total_seconds": s.total_point_seconds}
                    if s.total_point_seconds is not None
                    else {"feasible": 0.0}
                ),
                rationale="Backlog never converges at current generation/apply rates." if s.cdc_catchup_duration is None
                else ("Fits cutover window." if s.is_feasible else "Exceeds cutover window."),
            )
            for s in scenarios
        ]

        summary_parts = [f"{len(scenarios)} scenario(s) evaluated", f"{len(feasible_scenarios)} feasible within cutover window"]
        if infeasible_backlog:
            summary_parts.append(f"{len(infeasible_backlog)} scenario(s) have a CDC backlog that never converges")

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.PREDICTION,
            summary="; ".join(summary_parts) + ".",
            explanation=Explanation(
                summary="Deterministic queueing/throughput arithmetic; no scenario is marked cutover-ready unless "
                "canonical readiness authorities independently confirm it -- this is an estimate, not a readiness decision.",
                supporting_facts=[f"worker_counts_evaluated={worker_counts}"],
                assumptions=["±20% uncertainty band applied uniformly to point estimates"],
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=0.8,
                missing_information=["no live telemetry sampled; inputs are caller-supplied static rates"],
            ),
            predictions=predictions,
            optimization=OptimizationResult(objective="LOWEST_DOWNTIME", alternatives=alternatives),
            data={"scenarios": [s.to_dict() for s in scenarios]},
        )

    return producer

"""akaalEngine.intelligence.producers.runtime_health
======================================================
P7C.13 -- Runtime Health & Intelligence State.

Builds a read-only, dimensional trusted PROJECTION of canonical runtime facts
(migration lifecycle/runtime authority, telemetry throughput, CDC generation/
apply/backlog, worker/Fabric ownership, Validation #11 readout, governance/
approval state) into a typed IntelligenceResult. This module:

  - never creates a competing runtime-state store (no independent persistence
    of "current migration status" -- the projection is recomputed per request
    from whatever canonical facts the caller-supplied resolver returns);
  - never mutates canonical runtime, telemetry, CDC, Fabric, validation, or
    governance state (read-only projection only);
  - never turns missing/stale telemetry into a false "healthy" result -- a
    dimension with no data is UNKNOWN, never HEALTHY;
  - never recomputes Validation #11's own verdict -- it only relays whatever
    status the caller-supplied resolver reports Validation #11 as having
    produced.

Following the same conservative resolver-injection convention already used by
akaalEngine.intelligence.producers.estate_assessment / bootstrap.py: this
producer never performs discovery of canonical state itself. In production the
akaalPipeline layer (which has real access to RuntimeAuthority, TelemetryAuthority,
the CDC façade, Fabric ownership, ValidationAuthority) builds a RuntimeHealthInputs
snapshot from those real authorities and passes a resolver returning it; in unit
tests the resolver returns a fixture snapshot directly.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, List, Mapping, Optional

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


class DimensionStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BOTTLENECKED = "BOTTLENECKED"
    CRITICAL = "CRITICAL"
    NOT_READY = "NOT_READY"
    UNKNOWN = "UNKNOWN"


_SEVERITY_BY_STATUS = {
    DimensionStatus.CRITICAL: "HIGH",
    DimensionStatus.BOTTLENECKED: "HIGH",
    DimensionStatus.NOT_READY: "MEDIUM",
    DimensionStatus.DEGRADED: "MEDIUM",
    DimensionStatus.UNKNOWN: "LOW",
    DimensionStatus.HEALTHY: "LOW",
}

# Dimensions worse than HEALTHY, in ascending-then-CRITICAL severity order, used
# to fold per-dimension statuses into a single overall status without ever
# letting UNKNOWN silently outrank a genuinely observed problem.
_OVERALL_PRECEDENCE = [
    DimensionStatus.CRITICAL,
    DimensionStatus.BOTTLENECKED,
    DimensionStatus.NOT_READY,
    DimensionStatus.DEGRADED,
]


@dataclass(frozen=True)
class RuntimeHealthInputs:
    """Read-only snapshot of canonical facts this producer projects into
    dimensional health. Every field is optional and independently omittable --
    a caller (or resolver) that cannot supply a dimension leaves it as None,
    which this producer reports as UNKNOWN rather than guessing.

    Field shapes (all keys optional within each mapping):
      transport:  {throughput_rows_per_sec, baseline_rows_per_sec}
      cdc:        {generation_rate, apply_rate, backlog_size, backlog_trend
                    ("increasing"|"stable"|"decreasing"), lag_seconds}
      validation: {status ("HEALTHY"|"DEGRADED"|"FAILED"|"IN_PROGRESS"),
                    mismatch_count}
      workers:    {total, healthy, unhealthy}
      fabric:     {ownership_valid (bool), fencing_conflicts (int),
                    lease_valid (bool)}
      resources:  {cpu_pct, memory_pct, storage_pct, staging_pct}
      governance: {approvals_pending (int), security_blocking (bool),
                    cutover_ready (bool)}
    """

    migration_id: str = ""
    transport: Optional[Mapping[str, Any]] = None
    cdc: Optional[Mapping[str, Any]] = None
    validation: Optional[Mapping[str, Any]] = None
    workers: Optional[Mapping[str, Any]] = None
    fabric: Optional[Mapping[str, Any]] = None
    resources: Optional[Mapping[str, Any]] = None
    governance: Optional[Mapping[str, Any]] = None
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stale_after_seconds: Optional[float] = None
    # Explicitly PLATFORM-SCOPED, never migration-scoped: e.g. total worker count
    # observed for the whole engine-gateway process this migration happens to be
    # served by. NEVER fed into any dimension's HEALTHY/DEGRADED/BOTTLENECKED
    # status and NEVER used to raise, lower, or suppress `workers` (which stays
    # UNKNOWN when no genuine migration-scoped worker/task read exists) or any
    # other dimension. Carried only so downstream consumers can see *why*
    # WORKERS is UNKNOWN despite the process visibly running workers, without
    # ever mistaking this count for this migration's own worker health.
    platform_context: Optional[Mapping[str, Any]] = None


RuntimeHealthResolver = Callable[[IntelligenceRequest, IntelligenceContext], RuntimeHealthInputs]


def _ratio_status(
    numerator: Optional[float],
    denominator: Optional[float],
    *,
    healthy_at: float,
    degraded_at: float,
    below_status: DimensionStatus,
) -> DimensionStatus:
    if numerator is None or denominator is None:
        return DimensionStatus.UNKNOWN
    try:
        numerator = float(numerator)
        denominator = float(denominator)
    except (TypeError, ValueError):
        return DimensionStatus.UNKNOWN
    if denominator <= 0:
        # A non-positive baseline/generation-rate cannot support a meaningful
        # ratio; refuse to invent a status rather than dividing by zero.
        return DimensionStatus.UNKNOWN
    if numerator < 0:
        return DimensionStatus.UNKNOWN
    ratio = numerator / denominator
    if ratio >= healthy_at:
        return DimensionStatus.HEALTHY
    if ratio >= degraded_at:
        return DimensionStatus.DEGRADED
    return below_status


def _evaluate_transport(transport: Optional[Mapping[str, Any]]) -> tuple[DimensionStatus, List[str]]:
    if not transport:
        return DimensionStatus.UNKNOWN, ["no transport telemetry supplied"]
    status = _ratio_status(
        transport.get("throughput_rows_per_sec"),
        transport.get("baseline_rows_per_sec"),
        healthy_at=0.85,
        degraded_at=0.5,
        below_status=DimensionStatus.BOTTLENECKED,
    )
    facts = [
        f"throughput_rows_per_sec={transport.get('throughput_rows_per_sec')!r}",
        f"baseline_rows_per_sec={transport.get('baseline_rows_per_sec')!r}",
    ]
    return status, facts


def _evaluate_cdc(cdc: Optional[Mapping[str, Any]]) -> tuple[DimensionStatus, List[str]]:
    if not cdc:
        return DimensionStatus.UNKNOWN, ["no CDC telemetry supplied"]
    status = _ratio_status(
        cdc.get("apply_rate"),
        cdc.get("generation_rate"),
        healthy_at=0.95,
        degraded_at=0.6,
        below_status=DimensionStatus.BOTTLENECKED,
    )
    facts = [
        f"generation_rate={cdc.get('generation_rate')!r}",
        f"apply_rate={cdc.get('apply_rate')!r}",
        f"backlog_size={cdc.get('backlog_size')!r}",
        f"backlog_trend={cdc.get('backlog_trend')!r}",
    ]
    if status in (DimensionStatus.HEALTHY, DimensionStatus.DEGRADED) and cdc.get("backlog_trend") == "increasing":
        # A growing backlog is a genuine observed fact even when the
        # instantaneous apply/generation ratio still looks acceptable --
        # never let a momentary ratio mask a diverging queue.
        status = DimensionStatus.DEGRADED if status == DimensionStatus.HEALTHY else DimensionStatus.BOTTLENECKED
    return status, facts


def _evaluate_validation(validation: Optional[Mapping[str, Any]]) -> tuple[DimensionStatus, List[str]]:
    if not validation or not validation.get("status"):
        return DimensionStatus.UNKNOWN, ["no Validation #11 readout supplied"]
    raw = str(validation["status"]).upper()
    mapped = {
        "HEALTHY": DimensionStatus.HEALTHY,
        "PASSED": DimensionStatus.HEALTHY,
        "IN_PROGRESS": DimensionStatus.DEGRADED,
        "DEGRADED": DimensionStatus.DEGRADED,
        "FAILED": DimensionStatus.CRITICAL,
    }.get(raw, DimensionStatus.UNKNOWN)
    facts = [f"validation_status(raw)={raw!r}", f"mismatch_count={validation.get('mismatch_count')!r}"]
    return mapped, facts


def _evaluate_workers(workers: Optional[Mapping[str, Any]]) -> tuple[DimensionStatus, List[str]]:
    if not workers or workers.get("total") is None:
        return DimensionStatus.UNKNOWN, ["no worker telemetry supplied"]
    status = _ratio_status(
        workers.get("healthy"),
        workers.get("total"),
        healthy_at=1.0,
        degraded_at=0.75,
        below_status=DimensionStatus.BOTTLENECKED,
    )
    facts = [f"healthy={workers.get('healthy')!r}", f"total={workers.get('total')!r}"]
    return status, facts


def _evaluate_fabric(fabric: Optional[Mapping[str, Any]]) -> tuple[DimensionStatus, List[str]]:
    if not fabric or fabric.get("ownership_valid") is None:
        return DimensionStatus.UNKNOWN, ["no Fabric ownership/fencing telemetry supplied"]
    if not fabric.get("ownership_valid") or not fabric.get("lease_valid", True):
        return DimensionStatus.CRITICAL, [f"ownership_valid={fabric.get('ownership_valid')!r}", f"lease_valid={fabric.get('lease_valid')!r}"]
    conflicts = fabric.get("fencing_conflicts") or 0
    status = DimensionStatus.HEALTHY if conflicts == 0 else DimensionStatus.DEGRADED
    return status, [f"fencing_conflicts={conflicts!r}"]


def _rank(status: DimensionStatus) -> int:
    try:
        return _OVERALL_PRECEDENCE.index(status)
    except ValueError:
        return len(_OVERALL_PRECEDENCE)


def _evaluate_resources(resources: Optional[Mapping[str, Any]]) -> tuple[DimensionStatus, List[str]]:
    if not resources:
        return DimensionStatus.UNKNOWN, ["no resource telemetry supplied"]
    keys = ("cpu_pct", "memory_pct", "storage_pct", "staging_pct")
    facts = [f"{key}={resources.get(key)!r}" for key in keys]
    if not any(resources.get(key) is not None for key in keys):
        return DimensionStatus.UNKNOWN, facts

    worst = DimensionStatus.HEALTHY
    for key in keys:
        value = resources.get(key)
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if value >= 95.0:
            level = DimensionStatus.CRITICAL
        elif value >= 85.0:
            level = DimensionStatus.BOTTLENECKED
        elif value >= 70.0:
            level = DimensionStatus.DEGRADED
        else:
            level = DimensionStatus.HEALTHY
        if _rank(level) < _rank(worst):
            worst = level
    return worst, facts


def _evaluate_governance(governance: Optional[Mapping[str, Any]]) -> tuple[DimensionStatus, List[str]]:
    if not governance or governance.get("cutover_ready") is None:
        return DimensionStatus.UNKNOWN, ["no governance/cutover-readiness telemetry supplied"]
    if governance.get("security_blocking"):
        return DimensionStatus.CRITICAL, ["security_blocking=True"]
    if governance.get("cutover_ready"):
        return DimensionStatus.HEALTHY, [f"approvals_pending={governance.get('approvals_pending')!r}"]
    return DimensionStatus.NOT_READY, [f"approvals_pending={governance.get('approvals_pending')!r}"]


_DIMENSION_EVALUATORS = {
    "TRANSPORT": _evaluate_transport,
    "CDC": _evaluate_cdc,
    "VALIDATION": _evaluate_validation,
    "WORKERS": _evaluate_workers,
    "FABRIC": _evaluate_fabric,
    "RESOURCES": _evaluate_resources,
    "CUTOVER": _evaluate_governance,
}


def _overall_status(dimension_statuses: Mapping[str, DimensionStatus]) -> DimensionStatus:
    observed = [s for s in dimension_statuses.values() if s != DimensionStatus.UNKNOWN]
    if not observed:
        return DimensionStatus.UNKNOWN
    for candidate in _OVERALL_PRECEDENCE:
        if candidate in observed:
            return candidate
    return DimensionStatus.HEALTHY


def make_runtime_health_producer(resolver: RuntimeHealthResolver):
    """Returns an IntelligenceKernel-compatible producer for the runtime-health
    projection. `resolver` is injected rather than owned here: this producer
    performs zero canonical-state discovery of its own."""

    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        inputs = resolver(request, context)
        if inputs is None:
            raise IntelligenceValidationError(
                "Runtime health resolver returned no RuntimeHealthInputs snapshot. "
                "Refusing to fabricate a health projection with no canonical facts."
            )

        dimension_statuses: dict = {}
        dimension_facts: dict = {}
        for name, evaluator in _DIMENSION_EVALUATORS.items():
            source = {
                "TRANSPORT": inputs.transport,
                "CDC": inputs.cdc,
                "VALIDATION": inputs.validation,
                "WORKERS": inputs.workers,
                "FABRIC": inputs.fabric,
                "RESOURCES": inputs.resources,
                "CUTOVER": inputs.governance,
            }[name]
            status, facts = evaluator(source)
            dimension_statuses[name] = status
            dimension_facts[name] = facts

        overall = _overall_status(dimension_statuses)

        unknown_dims = [n for n, s in dimension_statuses.items() if s == DimensionStatus.UNKNOWN]
        observed_count = len(dimension_statuses) - len(unknown_dims)
        evidence_coverage = observed_count / len(dimension_statuses) if dimension_statuses else 0.0

        findings = [
            DiagnosticFinding(
                code=f"RUNTIME_HEALTH:{name}:{status.value}",
                severity=_SEVERITY_BY_STATUS[status],
                message=f"{name} dimension observed as {status.value}.",
                evidence_refs=list(dimension_facts[name]),
            )
            for name, status in dimension_statuses.items()
            if status not in (DimensionStatus.HEALTHY, DimensionStatus.UNKNOWN)
        ]

        supporting_facts = [f"{name}={status.value}" for name, status in dimension_statuses.items()]
        contradictions: List[str] = []
        if inputs.stale_after_seconds is not None:
            try:
                observed_dt = datetime.fromisoformat(inputs.observed_at)
                age = (datetime.now(timezone.utc) - observed_dt).total_seconds()
                if age > inputs.stale_after_seconds:
                    contradictions.append(
                        f"observed_at is {age:.1f}s old, exceeding stale_after_seconds="
                        f"{inputs.stale_after_seconds}; treat this projection as STALE, not current."
                    )
            except ValueError:
                contradictions.append("observed_at is not a valid ISO timestamp; freshness could not be verified.")

        assumptions: List[str] = []
        if inputs.stale_after_seconds is None:
            assumptions.append("No explicit staleness bound (stale_after_seconds) was supplied for this snapshot.")
        if inputs.platform_context and dimension_statuses.get("WORKERS") == DimensionStatus.UNKNOWN:
            assumptions.append(
                "platform_context reflects the whole engine-gateway process (all migrations it may be "
                "serving), NOT this migration specifically -- it is never used to infer WORKERS health for "
                "this migration, which remains UNKNOWN because no migration-scoped worker/task read exists."
            )

        summary = (
            f"Runtime health for migration {inputs.migration_id or context.subject_id!r}: "
            f"overall={overall.value}, "
            f"{len(dimension_statuses) - len(unknown_dims)}/{len(dimension_statuses)} dimensions observed."
        )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.DERIVED_FACT,
            summary=summary,
            explanation=Explanation(
                summary="Deterministic per-dimension projection over canonical telemetry supplied by a "
                "trusted resolver; dimensions without a canonical observation are UNKNOWN, never assumed healthy.",
                supporting_facts=supporting_facts,
                contradictions=contradictions,
                assumptions=assumptions,
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=evidence_coverage,
                source_freshness=inputs.observed_at,
                missing_information=[f"{name}: no data supplied" for name in unknown_dims],
            ),
            findings=findings,
            data={
                "migration_id": inputs.migration_id or context.subject_id,
                "overall_status": overall.value,
                "dimensions": {
                    name: {
                        "status": status.value,
                        "facts": dimension_facts[name],
                    }
                    for name, status in dimension_statuses.items()
                },
                # Never a dimension, never aggregated into overall_status: a
                # process-wide observation explicitly labeled so downstream
                # consumers (P7C.14+) cannot mistake it for this migration's
                # own worker health.
                "platform_context": dict(inputs.platform_context) if inputs.platform_context else None,
                "observed_at": inputs.observed_at,
            },
        )

    return producer

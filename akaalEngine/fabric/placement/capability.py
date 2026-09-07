"""
akaalEngine.fabric.placement.capability
==========================================
P7B.13 -- Capability-Aware Placement.

Answers exactly one question: "which execution sites can physically and functionally
execute this plan?" -- derived from requirements the CALLER supplies (in production,
derived from the existing canonical ExecutionPlan -- this module never re-derives plan
requirements itself, never constructs a second ExecutionPlan, and never reaches into
akaalPipeline.orchestration to read one; the caller reads the canonical plan and hands
this module a `CapabilityRequirement`).

ABSOLUTE LAW:

    UNSUPPORTED CAPABILITY CANNOT EXECUTE.
    CAPABILITY ADVERTISEMENT != TRUSTED CAPABILITY.

A site's `ExecutionSite.capabilities` frozenset is itself just a claim recorded at
registration time (see akaalEngine.fabric.execution_site) -- this module does not
re-verify that claim's truthfulness (that remains execution_site's/site
certification's job), but it DOES refuse to evaluate capability for any site that is not
at least SiteTrustState.REGISTERED, and never accepts a `CapabilityRequirement` or
`CapacityOffer` whose provenance is empty/UNKNOWN as if it were meaningful (an untrusted
worker cannot grant itself eligibility merely by claiming a capability with no stated
source).

This module makes NO authorization decision (that is P7B.14) and NO residency decision
(that is P7B.15) -- a capability-satisfied site can still be rejected by either of those
later stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Tuple

from akaalEngine.fabric.execution_site.models import ExecutionSite, SiteTrustState


class CapabilityEvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class CapacityOffer:
    """
    A site's caller-supplied resource capacity claim at evaluation time. This is NOT
    persisted trust state and NOT verified by this module -- callers in production
    source this from the elastic worker fabric (P7B.22), which is itself responsible for
    deciding how much to trust a given worker's self-reported numbers. `provenance`
    must be non-empty; an offer with empty/"UNKNOWN" provenance is refused outright by
    `evaluate_capability` rather than silently treated as zero capacity (silently
    treating it as zero would incorrectly reject a genuinely capable site; refusing the
    evaluation outright forces the caller to notice the missing provenance instead).
    """
    cpu_cores: Optional[float] = None
    memory_mb: Optional[int] = None
    disk_mb: Optional[int] = None
    concurrency_slots: Optional[int] = None
    throughput_mbps: Optional[float] = None
    provenance: str = ""

    def __post_init__(self) -> None:
        for name in ("cpu_cores", "memory_mb", "disk_mb", "concurrency_slots", "throughput_mbps"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise CapabilityEvaluationError(f"CapacityOffer.{name} must be >= 0 if supplied; got {value!r}.")


@dataclass(frozen=True)
class CapabilityRequirement:
    """
    What an ExecutionPlan (read by the caller, never re-derived here) genuinely requires
    of a candidate execution site. `required_capabilities` are opaque capability strings
    matched exactly against `ExecutionSite.capabilities` -- this module never fuzzy-
    matches, substitutes, or normalizes capability names (a site advertising
    "postgresql" cannot satisfy a requirement for "oracle" no matter how the strings are
    compared).
    """
    required_capabilities: FrozenSet[str] = field(default_factory=frozenset)
    min_cpu_cores: Optional[float] = None
    min_memory_mb: Optional[int] = None
    min_disk_mb: Optional[int] = None
    min_concurrency_slots: Optional[int] = None
    min_throughput_mbps: Optional[float] = None
    requires_staging_capable: bool = False
    plan_reference: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.required_capabilities, frozenset):
            object.__setattr__(self, "required_capabilities", frozenset(self.required_capabilities))
        if not self.plan_reference or not self.plan_reference.strip():
            raise CapabilityEvaluationError(
                "CapabilityRequirement.plan_reference must be non-empty -- a capability "
                "evaluation must always be traceable to the specific plan it was derived "
                "from, never anonymous."
            )


@dataclass(frozen=True)
class CapabilityEvaluation:
    """Immutable, explainable evaluation outcome for exactly one candidate site against
    exactly one CapabilityRequirement. Carries structured reasons for both acceptance and
    rejection -- see the Group-2 explainability requirement (P7B.16 consumes this)."""
    site_id: str
    plan_reference: str
    satisfied: bool
    missing_capabilities: FrozenSet[str] = field(default_factory=frozenset)
    insufficient_dimensions: Tuple[str, ...] = field(default_factory=tuple)
    reasons: Tuple[str, ...] = field(default_factory=tuple)


def evaluate_capability(
    site: ExecutionSite,
    requirement: CapabilityRequirement,
    capacity: Optional[CapacityOffer] = None,
) -> CapabilityEvaluation:
    """
    Pure function: no I/O, no mutation, no authorization/residency decision. A site below
    SiteTrustState.REGISTERED (i.e. UNREGISTERED) or in SiteTrustState.REVOKED can never
    be evaluated as capable, regardless of its advertised capabilities -- an unregistered
    or revoked site's capability claims carry no weight at all.
    """
    reasons: list = []
    missing = frozenset()
    insufficient: list = []

    if site.trust_state in (SiteTrustState.UNREGISTERED, SiteTrustState.REVOKED):
        return CapabilityEvaluation(
            site_id=site.site_id, plan_reference=requirement.plan_reference, satisfied=False,
            missing_capabilities=requirement.required_capabilities,
            reasons=(f"site trust_state is {site.trust_state.value}; capability cannot be evaluated for an unregistered/revoked site.",),
        )

    missing = requirement.required_capabilities - site.capabilities
    if missing:
        reasons.append(f"missing required capabilities: {sorted(missing)}")
    else:
        for cap in sorted(requirement.required_capabilities):
            reasons.append(f"required capability satisfied: {cap}")

    if requirement.requires_staging_capable and not site.staging_capable:
        insufficient.append("staging_capable")
        reasons.append("plan requires staging capability; site is not staging_capable")

    dimension_checks = (
        ("min_cpu_cores", "cpu_cores"),
        ("min_memory_mb", "memory_mb"),
        ("min_disk_mb", "disk_mb"),
        ("min_concurrency_slots", "concurrency_slots"),
        ("min_throughput_mbps", "throughput_mbps"),
    )
    any_resource_requirement = any(getattr(requirement, req_attr) is not None for req_attr, _ in dimension_checks)
    if any_resource_requirement:
        if capacity is None or not capacity.provenance or not capacity.provenance.strip():
            for req_attr, dim in dimension_checks:
                if getattr(requirement, req_attr) is not None:
                    insufficient.append(dim)
            reasons.append(
                "plan has resource requirements but no provenance-bearing CapacityOffer was "
                "supplied; refusing to assume sufficient capacity."
            )
        else:
            for req_attr, dim in dimension_checks:
                required_value = getattr(requirement, req_attr)
                if required_value is None:
                    continue
                offered_value = getattr(capacity, dim)
                if offered_value is None or offered_value < required_value:
                    insufficient.append(dim)
                    reasons.append(f"insufficient {dim}: required {required_value}, offered {offered_value!r}")
                else:
                    reasons.append(f"sufficient {dim}: required {required_value}, offered {offered_value}")

    satisfied = not missing and not insufficient
    return CapabilityEvaluation(
        site_id=site.site_id,
        plan_reference=requirement.plan_reference,
        satisfied=satisfied,
        missing_capabilities=missing,
        insufficient_dimensions=tuple(insufficient),
        reasons=tuple(reasons),
    )

"""
akaalEngine.fabric.placement.cost
====================================
P7B.17 -- Cost / Egress / Capacity Intelligence.

NOT a cloud billing platform. Models estimated data-movement and compute cost inputs for
placement scoring (P7B.16) -- and, above everything else in this module, is honest about
what it does not know.

ABSOLUTE LAW:

    COST NEVER OVERRIDES SECURITY, CORRECTNESS, AUTHORIZATION OR RESIDENCY.

This module has no way to override anything -- it produces a `CostEstimate` that
`akaalEngine.fabric.placement.optimize` may only ever apply to candidates that
`akaalEngine.fabric.placement.engine` already accepted; there is no code path anywhere in
this package that lets a cost/capacity number resurrect a rejected candidate.

Truthfulness law: no fabricated cloud prices. A missing/unconfigured price input
produces `CostConfidence.UNKNOWN`, never a guessed number; a price input whose age
exceeds `max_price_age_seconds` (when supplied) produces `CostConfidence.STALE`. Only an
explicitly-supplied, fresh price/rate produces `CostConfidence.ESTIMATED`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class CostModelError(ValueError):
    pass


class CostConfidence(str, Enum):
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    ESTIMATED = "ESTIMATED"


@dataclass(frozen=True)
class PricingInput:
    """Caller-supplied pricing data (in production, sourced from operator-configured
    provider pricing, never invented here). `observed_at` lets `estimate_cost` detect
    staleness against `max_price_age_seconds`."""
    egress_cost_per_gb: Optional[float] = None
    cross_region_cost_per_gb: Optional[float] = None
    compute_cost_per_hour: Optional[float] = None
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: str = ""

    def __post_init__(self) -> None:
        for name in ("egress_cost_per_gb", "cross_region_cost_per_gb", "compute_cost_per_hour"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise CostModelError(f"PricingInput.{name} must be >= 0 if supplied; got {value!r}.")


@dataclass(frozen=True)
class MovementEstimate:
    """What is honestly known about the data this placement would move. `estimated_bytes`
    is None (not zero) when genuinely not estimable -- zero would falsely claim a known
    quantity of zero bytes."""
    estimated_bytes: Optional[int] = None
    is_cross_region: bool = False
    is_cross_cloud: bool = False
    estimated_duration_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        if self.estimated_bytes is not None and self.estimated_bytes < 0:
            raise CostModelError("MovementEstimate.estimated_bytes must be >= 0 if supplied.")
        if self.estimated_duration_seconds is not None and self.estimated_duration_seconds < 0:
            raise CostModelError("MovementEstimate.estimated_duration_seconds must be >= 0 if supplied.")


@dataclass(frozen=True)
class CostEstimate:
    site_id: str
    confidence: CostConfidence
    estimated_total_cost: Optional[float] = None
    estimated_egress_cost: Optional[float] = None
    estimated_compute_cost: Optional[float] = None
    reasons: tuple = field(default_factory=tuple)


def estimate_cost(
    site_id: str,
    movement: MovementEstimate,
    pricing: Optional[PricingInput],
    *,
    max_price_age_seconds: Optional[float] = None,
    now: Optional[datetime] = None,
) -> CostEstimate:
    """
    Pure function. Returns CostConfidence.UNKNOWN with `estimated_total_cost=None`
    whenever pricing is absent/unprovenanced, `estimated_bytes` is unknown, or the
    supplied pricing is stale relative to `max_price_age_seconds` -- never a guessed
    number in any of those cases.
    """
    if pricing is None or not pricing.provenance or not pricing.provenance.strip():
        return CostEstimate(site_id=site_id, confidence=CostConfidence.UNKNOWN,
                             reasons=("no provenance-bearing PricingInput supplied",))

    if max_price_age_seconds is not None:
        current = now or datetime.now(timezone.utc)
        observed = datetime.fromisoformat(pricing.observed_at)
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        if (current - observed).total_seconds() > max_price_age_seconds:
            return CostEstimate(site_id=site_id, confidence=CostConfidence.STALE,
                                 reasons=(f"pricing observed_at {pricing.observed_at!r} exceeds max_price_age_seconds={max_price_age_seconds}",))

    if movement.estimated_bytes is None:
        return CostEstimate(site_id=site_id, confidence=CostConfidence.UNKNOWN,
                             reasons=("estimated_bytes is unknown; refusing to fabricate an egress cost from an unknown volume",))

    gb = movement.estimated_bytes / (1024 ** 3)
    reasons = []
    egress_cost = None
    rate = pricing.cross_region_cost_per_gb if (movement.is_cross_region or movement.is_cross_cloud) else pricing.egress_cost_per_gb
    if rate is not None:
        egress_cost = gb * rate
        reasons.append(f"egress estimate: {gb:.4f} GB * {rate} = {egress_cost:.6f}")
    else:
        reasons.append("no applicable per-GB rate configured for this movement shape; egress cost left UNKNOWN-component")

    compute_cost = None
    if pricing.compute_cost_per_hour is not None and movement.estimated_duration_seconds is not None:
        hours = movement.estimated_duration_seconds / 3600.0
        compute_cost = hours * pricing.compute_cost_per_hour
        reasons.append(f"compute estimate: {hours:.4f} h * {pricing.compute_cost_per_hour} = {compute_cost:.6f}")

    if egress_cost is None and compute_cost is None:
        return CostEstimate(site_id=site_id, confidence=CostConfidence.UNKNOWN, reasons=tuple(reasons))

    total = (egress_cost or 0.0) + (compute_cost or 0.0)
    return CostEstimate(
        site_id=site_id, confidence=CostConfidence.ESTIMATED,
        estimated_total_cost=total, estimated_egress_cost=egress_cost, estimated_compute_cost=compute_cost,
        reasons=tuple(reasons),
    )

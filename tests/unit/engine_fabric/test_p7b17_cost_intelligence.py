"""
P7B.17 -- Cost/Egress/Capacity Intelligence: positive and truthfulness hostile tests.
"""

from datetime import datetime, timedelta, timezone

import pytest

from akaalEngine.fabric.placement.cost import (
    CostConfidence,
    CostModelError,
    MovementEstimate,
    PricingInput,
    estimate_cost,
)


def test_estimated_cost_when_pricing_and_volume_known():
    pricing = PricingInput(egress_cost_per_gb=0.09, provenance="operator-configured")
    movement = MovementEstimate(estimated_bytes=10 * 1024 ** 3)  # 10 GB
    result = estimate_cost("site-1", movement, pricing)
    assert result.confidence == CostConfidence.ESTIMATED
    assert result.estimated_total_cost == pytest.approx(0.9, rel=1e-6)


def test_cross_region_uses_cross_region_rate():
    pricing = PricingInput(egress_cost_per_gb=0.09, cross_region_cost_per_gb=0.20, provenance="operator-configured")
    movement = MovementEstimate(estimated_bytes=10 * 1024 ** 3, is_cross_region=True)
    result = estimate_cost("site-1", movement, pricing)
    assert result.estimated_total_cost == pytest.approx(2.0, rel=1e-6)


def test_no_pricing_supplied_is_unknown_never_fabricated():
    movement = MovementEstimate(estimated_bytes=1024 ** 3)
    result = estimate_cost("site-1", movement, None)
    assert result.confidence == CostConfidence.UNKNOWN
    assert result.estimated_total_cost is None


def test_unprovenanced_pricing_treated_as_unknown():
    pricing = PricingInput(egress_cost_per_gb=0.09, provenance="")
    movement = MovementEstimate(estimated_bytes=1024 ** 3)
    result = estimate_cost("site-1", movement, pricing)
    assert result.confidence == CostConfidence.UNKNOWN


def test_unknown_volume_never_produces_a_number():
    pricing = PricingInput(egress_cost_per_gb=0.09, provenance="operator-configured")
    movement = MovementEstimate(estimated_bytes=None)
    result = estimate_cost("site-1", movement, pricing)
    assert result.confidence == CostConfidence.UNKNOWN
    assert result.estimated_total_cost is None


def test_stale_pricing_rejected_not_used():
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    pricing = PricingInput(egress_cost_per_gb=0.09, provenance="operator-configured", observed_at=old)
    movement = MovementEstimate(estimated_bytes=1024 ** 3)
    result = estimate_cost("site-1", movement, pricing, max_price_age_seconds=3600)
    assert result.confidence == CostConfidence.STALE
    assert result.estimated_total_cost is None


def test_fresh_pricing_within_max_age_accepted():
    fresh = datetime.now(timezone.utc).isoformat()
    pricing = PricingInput(egress_cost_per_gb=0.09, provenance="operator-configured", observed_at=fresh)
    movement = MovementEstimate(estimated_bytes=1024 ** 3)
    result = estimate_cost("site-1", movement, pricing, max_price_age_seconds=3600)
    assert result.confidence == CostConfidence.ESTIMATED


def test_negative_price_rejected_at_construction():
    with pytest.raises(CostModelError):
        PricingInput(egress_cost_per_gb=-1.0, provenance="operator-configured")


def test_negative_bytes_rejected_at_construction():
    with pytest.raises(CostModelError):
        MovementEstimate(estimated_bytes=-5)


def test_zero_bytes_is_a_known_value_distinct_from_unknown():
    """Zero must never be conflated with 'unknown' -- a genuinely-zero-byte movement
    still produces an ESTIMATED (zero) cost, not UNKNOWN."""
    pricing = PricingInput(egress_cost_per_gb=0.09, provenance="operator-configured")
    movement = MovementEstimate(estimated_bytes=0)
    result = estimate_cost("site-1", movement, pricing)
    assert result.confidence == CostConfidence.ESTIMATED
    assert result.estimated_total_cost == 0.0

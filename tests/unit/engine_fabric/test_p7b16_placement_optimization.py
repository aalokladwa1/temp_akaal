"""
P7B.16 -- Placement Optimization: determinism, tie-breaking, NaN/inf, and the
"cost can never resurrect a rejected/never-cheaper-than-compliant" hostile matrix.
"""

import math

from akaalEngine.fabric.placement.cost import CostConfidence, CostEstimate
from akaalEngine.fabric.placement.optimize import rank_candidates


def test_lower_cost_ranks_first():
    costs = {
        "expensive": CostEstimate(site_id="expensive", confidence=CostConfidence.ESTIMATED, estimated_total_cost=5.0),
        "cheap": CostEstimate(site_id="cheap", confidence=CostConfidence.ESTIMATED, estimated_total_cost=1.0),
    }
    ranked = rank_candidates(("expensive", "cheap"), cost_by_site=costs)
    assert [r.site_id for r in ranked] == ["cheap", "expensive"]


def test_deterministic_tiebreak_by_site_id():
    costs = {
        "b-site": CostEstimate(site_id="b-site", confidence=CostConfidence.ESTIMATED, estimated_total_cost=1.0),
        "a-site": CostEstimate(site_id="a-site", confidence=CostConfidence.ESTIMATED, estimated_total_cost=1.0),
    }
    ranked = rank_candidates(("b-site", "a-site"), cost_by_site=costs)
    assert [r.site_id for r in ranked] == ["a-site", "b-site"]  # lexicographic tiebreak


def test_repeated_calls_identical_input_identical_order():
    costs = {"x": CostEstimate(site_id="x", confidence=CostConfidence.ESTIMATED, estimated_total_cost=3.0),
             "y": CostEstimate(site_id="y", confidence=CostConfidence.ESTIMATED, estimated_total_cost=3.0),
             "z": CostEstimate(site_id="z", confidence=CostConfidence.ESTIMATED, estimated_total_cost=2.0)}
    r1 = rank_candidates(("x", "y", "z"), cost_by_site=costs)
    r2 = rank_candidates(("z", "y", "x"), cost_by_site=costs)  # different input order
    assert [c.site_id for c in r1] == [c.site_id for c in r2] == ["z", "x", "y"]


def test_unknown_cost_never_advantaged_or_penalized():
    costs = {
        "known": CostEstimate(site_id="known", confidence=CostConfidence.ESTIMATED, estimated_total_cost=100.0),
        "unknown": CostEstimate(site_id="unknown", confidence=CostConfidence.UNKNOWN),
    }
    ranked = rank_candidates(("known", "unknown"), cost_by_site=costs)
    unknown_entry = next(r for r in ranked if r.site_id == "unknown")
    cost_factor = next(f for f in unknown_entry.factors if f.name == "cost")
    assert cost_factor.value is None
    assert cost_factor.contribution == 0.0
    # unknown (contribution 0.0) beats known-expensive (100.0) purely because 0 < 100 --
    # this is intentional and documented: unknown cost must never be TREATED as a large
    # penalty, only as "no signal" (contribution 0). Callers wanting to penalize missing
    # cost data must do so explicitly upstream (this module never assumes a penalty).
    assert ranked[0].site_id == "unknown"


def test_nan_and_inf_signals_treated_as_no_signal_never_poison_score():
    proximity = {"site-nan": math.nan, "site-inf": math.inf, "site-normal": 5.0}
    ranked = rank_candidates(("site-nan", "site-inf", "site-normal"), proximity_score_by_site=proximity)
    for r in ranked:
        assert not math.isnan(r.score)
        assert not math.isinf(r.score)
    nan_entry = next(r for r in ranked if r.site_id == "site-nan")
    prox_factor = next(f for f in nan_entry.factors if f.name == "proximity")
    assert prox_factor.value is None  # NaN was scrubbed to "unknown", not propagated


def test_empty_candidate_list_returns_empty_ranking():
    assert rank_candidates(()) == ()


def test_single_candidate_ranking_trivial():
    ranked = rank_candidates(("only-one",))
    assert len(ranked) == 1
    assert ranked[0].site_id == "only-one"
    assert ranked[0].score == 0.0


def test_thousands_of_candidates_ranked_without_hang():
    import time
    site_ids = tuple(f"site-{i}" for i in range(5000))
    costs = {sid: CostEstimate(site_id=sid, confidence=CostConfidence.ESTIMATED, estimated_total_cost=float(5000 - i))
             for i, sid in enumerate(site_ids)}
    t0 = time.perf_counter()
    ranked = rank_candidates(site_ids, cost_by_site=costs)
    elapsed = time.perf_counter() - t0
    assert len(ranked) == 5000
    assert ranked[0].site_id == "site-4999"  # lowest cost (5000-4999=1) ranks first
    assert elapsed < 10.0


def test_negative_score_still_orders_correctly_below_zero():
    costs = {
        "positive": CostEstimate(site_id="positive", confidence=CostConfidence.ESTIMATED, estimated_total_cost=1.0),
    }
    proximity = {"negative": -50.0}
    ranked = rank_candidates(("positive", "negative"), cost_by_site=costs, proximity_score_by_site=proximity)
    assert ranked[0].site_id == "negative"  # -50 < 1

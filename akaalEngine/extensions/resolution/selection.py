"""
akaalEngine.extensions.resolution.selection
===========================================
Deterministic strategy selection, capability satisfaction filtering, and ambiguity rejection.
"""

from __future__ import annotations

from typing import Optional, Sequence

from akaalEngine.extensions.compatibility.evaluator import CompatibilityEvaluator
from akaalEngine.extensions.errors.taxonomy import AmbiguousStrategyError, StrategyNotFoundError
from akaalEngine.extensions.models.strategy import StrategyContribution


class StrategySelector:
    """
    Selects the single best-matching strategy among candidates.
    """

    @classmethod
    def select(
        cls,
        candidates: Sequence[StrategyContribution],
        target_provider: str,
        target_authority: str,
        specific_strategy_id: Optional[str] = None,
        required_contract_version: Optional[str] = None,
        required_capabilities: Optional[Sequence[str]] = None,
    ) -> StrategyContribution:
        if not candidates:
            raise StrategyNotFoundError(
                f"No strategy candidates found for provider '{target_provider}' and authority '{target_authority}'."
            )

        # 1. Filter by specific strategy_id if requested
        if specific_strategy_id:
            filtered = [c for c in candidates if c.strategy_id.value == specific_strategy_id.strip().lower()]
            if not filtered:
                raise StrategyNotFoundError(
                    f"Requested strategy_id '{specific_strategy_id}' not found for provider '{target_provider}' and authority '{target_authority}'."
                )
            candidates = filtered

        # 2. Filter by contract version compatibility if required
        if required_contract_version:
            matching_contract = []
            for c in candidates:
                comp = CompatibilityEvaluator.evaluate(
                    target_name=f"Strategy {c.strategy_id}",
                    version_str=required_contract_version,
                    required_range=c.contract_version_range,
                )
                if comp.is_compatible:
                    matching_contract.append(c)
            if not matching_contract:
                raise StrategyNotFoundError(
                    f"No strategy for provider '{target_provider}' and authority '{target_authority}' satisfies required contract version '{required_contract_version}'."
                )
            candidates = matching_contract

        # 3. Filter by required capabilities if requested
        if required_capabilities:
            matching_caps = []
            req_caps_norm = {c.strip().upper() for c in required_capabilities}
            for c in candidates:
                strat_caps = {cap.capability_name for cap in c.capabilities if cap.is_supported}
                if req_caps_norm.issubset(strat_caps):
                    matching_caps.append(c)
            if not matching_caps:
                raise StrategyNotFoundError(
                    f"No strategy for provider '{target_provider}' and authority '{target_authority}' satisfies all required capabilities: {list(req_caps_norm)}."
                )
            candidates = matching_caps

        # 4. Sort by priority (descending)
        sorted_candidates = sorted(candidates, key=lambda s: s.priority, reverse=True)
        top_priority = sorted_candidates[0].priority
        top_candidates = [c for c in sorted_candidates if c.priority == top_priority]

        if len(top_candidates) > 1:
            competing_ids = [c.strategy_id.value for c in top_candidates]
            raise AmbiguousStrategyError(
                f"Ambiguous strategy resolution for provider '{target_provider}' and authority '{target_authority}': multiple active strategies share priority {top_priority}: {competing_ids}."
            )

        return top_candidates[0]

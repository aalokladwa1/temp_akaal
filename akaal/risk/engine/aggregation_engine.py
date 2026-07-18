"""
Akaal — Risk Aggregation Engine
===============================
Single-responsibility engine executing grouping, deduplication, and risk score aggregation.
Deduplicates risk evidence to prevent artificial score inflation.
"""

from typing import List, Tuple, Dict, Any
from akaal.risk.models.risk_item import RiskItem
from akaal.risk.models.risk_score import RiskScore
from akaal.risk.models.evidence import RiskEvidenceGraph, EvidenceNode
from akaal.risk.registry.scoring_registry import ScoringRegistry


class AggregationEngine:
    """Aggregates and deduplicates risk items into overall risk scores."""

    def aggregate(self, raw_items: List[RiskItem]) -> Tuple[List[RiskItem], RiskScore, RiskEvidenceGraph]:
        seen_fingerprints = set()
        deduped_items: List[RiskItem] = []
        evidence_graph = RiskEvidenceGraph()

        for item in raw_items:
            fp = item.risk_fingerprint or item.risk_id
            if fp not in seen_fingerprints:
                seen_fingerprints.add(fp)
                deduped_items.append(item)

                ev_node = EvidenceNode(
                    evidence_id=f"EV-{item.risk_id}",
                    node_type="RISK_ITEM",
                    canonical_id=item.canonical_references[0].canonical_id if item.canonical_references else None,
                    analyzer_name=item.detection_engine,
                    reason=item.root_cause,
                )
                evidence_graph.add_node(ev_node)

        # Calculate score
        score_val = 0.0
        for item in deduped_items:
            sev_str = str(item.severity.value if hasattr(item.severity, "value") else item.severity).lower()
            weight_key = f"{sev_str}_severity_weight"
            score_val += ScoringRegistry.get_threshold(weight_key, 1.0)

        score_obj = RiskScore(
            overall_risk_score=min(100.0, score_val),
            compatibility_risk_score=min(100.0, score_val * 0.4),
            performance_risk_score=min(100.0, score_val * 0.2),
            data_loss_risk_score=min(100.0, score_val * 0.3),
        )

        return deduped_items, score_obj, evidence_graph

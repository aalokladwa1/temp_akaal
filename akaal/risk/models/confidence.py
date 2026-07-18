"""
Akaal — Multi-Dimensional Confidence Model
==========================================
Composed confidence score evaluating metadata, rule provenance, analyzer, capability, and evidence strength.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ConfidenceScore:
    metadata_confidence: float = 100.0
    rule_confidence: float = 100.0
    analyzer_confidence: float = 100.0
    capability_confidence: float = 100.0
    evidence_confidence: float = 100.0

    @property
    def overall_confidence(self) -> float:
        weights = [
            (self.metadata_confidence, 0.2),
            (self.rule_confidence, 0.2),
            (self.analyzer_confidence, 0.2),
            (self.capability_confidence, 0.2),
            (self.evidence_confidence, 0.2),
        ]
        return round(sum(val * w for val, w in weights), 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata_confidence": self.metadata_confidence,
            "rule_confidence": self.rule_confidence,
            "analyzer_confidence": self.analyzer_confidence,
            "capability_confidence": self.capability_confidence,
            "evidence_confidence": self.evidence_confidence,
            "overall_confidence": self.overall_confidence,
        }

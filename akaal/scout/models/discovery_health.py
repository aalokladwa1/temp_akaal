"""
Akaal — Discovery Health & Recommendations Models
=================================================
Calculates completeness, permissions, confidence, and overall health scores.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class DiscoveryRecommendation:
    category: str  # "PROVIDER", "PERMISSIONS", "VERSION", "STORAGE", "CLUSTER", "CAPABILITY"
    severity: str  # "INFO", "WARNING", "HIGH"
    observation: str
    recommendation_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "observation": self.observation,
            "recommendation_text": self.recommendation_text,
        }


@dataclass
class DiscoveryHealth:
    """Discovery Health Score (0-100) and structured observations."""
    completeness_score: float = 100.0
    permission_score: float = 100.0
    confidence_score: float = 100.0
    provider_compatibility_score: float = 100.0
    warning_score: float = 100.0
    overall_health_score: float = 100.0

    recommendations: List[DiscoveryRecommendation] = field(default_factory=list)

    def calculate_overall(self) -> float:
        scores = [
            self.completeness_score,
            self.permission_score,
            self.confidence_score,
            self.provider_compatibility_score,
            self.warning_score,
        ]
        self.overall_health_score = sum(scores) / len(scores)
        return self.overall_health_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "completeness_score": round(self.completeness_score, 2),
            "permission_score": round(self.permission_score, 2),
            "confidence_score": round(self.confidence_score, 2),
            "provider_compatibility_score": round(self.provider_compatibility_score, 2),
            "warning_score": round(self.warning_score, 2),
            "overall_health_score": round(self.overall_health_score, 2),
            "recommendations": [r.to_dict() for r in self.recommendations],
        }

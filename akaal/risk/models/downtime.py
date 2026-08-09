"""
Akaal — Downtime Estimation Model
=================================
Downtime estimation model calculating estimated cutover downtime.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DowntimeEstimate:
    estimated_downtime_minutes: Optional[float] = None
    confidence_score: float = 0.0
    cutover_strategy: str = "OFFLINE_BULK"
    cdc_available: bool = False
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimated_downtime_minutes": round(self.estimated_downtime_minutes, 2) if self.estimated_downtime_minutes is not None else None,
            "confidence_score": round(self.confidence_score, 2),
            "cutover_strategy": self.cutover_strategy,
            "cdc_available": self.cdc_available,
            "evidence": self.evidence,
        }

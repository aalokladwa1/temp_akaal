"""
Akaal — Capability Inventory Model
==================================
Structured inventory of database engine capabilities with confidence scoring.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class CapabilityConfidence:
    """Confidence score and detection evidence for a single feature flag."""
    supported: bool = False
    confidence_score: int = 100  # 0 to 100
    detection_method: str = "Native Metadata Inspection"
    evidence: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supported": self.supported,
            "confidence_score": self.confidence_score,
            "detection_method": self.detection_method,
            "evidence": self.evidence,
            "notes": self.notes,
        }


@dataclass
class CapabilityInventory:
    """
    Dedicated capability model consumed by Rulebook, Planner, Risk, and Advisor.
    Includes confidence scoring per capability.
    """
    supports_cdc: bool = False
    supports_partitioning: bool = False
    supports_compression: bool = False
    supports_encryption: bool = False
    supports_replication: bool = False
    supports_json: bool = False
    supports_xml: bool = False
    supports_spatial: bool = False
    supports_materialized_views: bool = False
    supports_stored_procedures: bool = False
    supports_functions: bool = False
    supports_triggers: bool = False
    supports_sequences: bool = False
    supports_generated_columns: bool = False
    supports_lob_streaming: bool = False
    
    confidence_scores: Dict[str, CapabilityConfidence] = field(default_factory=dict)
    extra_capabilities: Dict[str, Any] = field(default_factory=dict)

    def set_capability(
        self,
        cap_name: str,
        supported: bool,
        confidence_score: int = 100,
        detection_method: str = "Native Metadata Inspection",
        evidence: str = "",
        notes: str = "",
    ) -> None:
        if hasattr(self, cap_name):
            setattr(self, cap_name, supported)
        self.confidence_scores[cap_name] = CapabilityConfidence(
            supported=supported,
            confidence_score=confidence_score,
            detection_method=detection_method,
            evidence=evidence,
            notes=notes,
        )

    def get_average_confidence(self) -> float:
        if not self.confidence_scores:
            return 100.0
        return sum(c.confidence_score for c in self.confidence_scores.values()) / len(self.confidence_scores)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supports_cdc": self.supports_cdc,
            "supports_partitioning": self.supports_partitioning,
            "supports_compression": self.supports_compression,
            "supports_encryption": self.supports_encryption,
            "supports_replication": self.supports_replication,
            "supports_json": self.supports_json,
            "supports_xml": self.supports_xml,
            "supports_spatial": self.supports_spatial,
            "supports_materialized_views": self.supports_materialized_views,
            "supports_stored_procedures": self.supports_stored_procedures,
            "supports_functions": self.supports_functions,
            "supports_triggers": self.supports_triggers,
            "supports_sequences": self.supports_sequences,
            "supports_generated_columns": self.supports_generated_columns,
            "supports_lob_streaming": self.supports_lob_streaming,
            "confidence_scores": {k: v.to_dict() for k, v in self.confidence_scores.items()},
            "average_confidence": round(self.get_average_confidence(), 2),
            "extra_capabilities": self.extra_capabilities,
        }

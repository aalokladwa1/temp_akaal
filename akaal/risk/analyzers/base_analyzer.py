"""
Akaal — Base Risk Analyzer Plugin Interface
===========================================
Passive BaseAnalyzer plugin interface exposing Governance Metadata.
Analyzers receive CanonicalMigrationModel and produce RiskItems without mutating shared state.
"""

import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.risk_item import RiskItem


class BaseAnalyzer(ABC):
    """Abstract Risk Analyzer plugin interface."""

    analyzer_id: str = "base_analyzer"
    analyzer_name: str = "Base Analyzer"
    semantic_version: str = "1.0.0"
    supported_risk_schema: str = "1.0.0"
    supported_canonical_schema: str = "1.0.0"
    lifecycle_state: str = "ACTIVE"

    @abstractmethod
    def analyze(self, ctx: RiskContext) -> List[RiskItem]:
        """Analyze CanonicalMigrationModel and return detected RiskItems."""

    def metadata(self) -> Dict[str, Any]:
        return {
            "analyzer_id": self.analyzer_id,
            "analyzer_name": self.analyzer_name,
            "semantic_version": self.semantic_version,
            "supported_risk_schema": self.supported_risk_schema,
            "supported_canonical_schema": self.supported_canonical_schema,
            "lifecycle_state": self.lifecycle_state,
            "checksum": self.checksum(),
        }

    def checksum(self) -> str:
        raw = f"{self.analyzer_id}:{self.semantic_version}:{self.lifecycle_state}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def validate(self) -> bool:
        return True

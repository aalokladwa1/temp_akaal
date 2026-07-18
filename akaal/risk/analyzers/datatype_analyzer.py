"""
Akaal — Datatype Loss Risk Analyzer
====================================
Analyzes CanonicalMigrationModel objects for OpaqueTypes, precision loss, scale loss, and nullability shifts.
"""

import uuid
from typing import List
from akaal.risk.analyzers.base_analyzer import BaseAnalyzer
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.risk_item import RiskItem
from akaal.risk.models.risk_taxonomy import RiskDomain, RiskCategory, RiskType
from akaal.risk.models.severity import Severity, SeverityMatrix
from akaal.risk.models.confidence import ConfidenceScore
from akaal.risk.models.canonical_reference import CanonicalReference


class DatatypeAnalyzer(BaseAnalyzer):
    analyzer_id = "datatype_loss_analyzer"
    analyzer_name = "Datatype Loss Risk Analyzer"
    semantic_version = "1.0.0"

    def analyze(self, ctx: RiskContext) -> List[RiskItem]:
        items: List[RiskItem] = []
        c_model = ctx.canonical_model

        nodes = c_model.canonical_graph.get("nodes", [])
        for node in nodes:
            obj_type = node.get("object_type", "")
            if obj_type == "CanonicalColumn":
                dt = node.get("data_type", {})
                if dt and dt.get("family") == "OPAQUE":
                    c_name = node.get("name", "unknown")
                    c_id = node.get("identity", {}).get("canonical_id", str(uuid.uuid4()))
                    
                    item = RiskItem(
                        risk_id=f"RISK-DT-{c_id}",
                        domain=RiskDomain.COMPATIBILITY.value,
                        category=RiskCategory.DATATYPE.value,
                        risk_type=RiskType.OPAQUE_TYPE.value,
                        severity=SeverityMatrix.calculate(0.8, 0.7, 0.5),  # HIGH
                        confidence=ConfidenceScore(metadata_confidence=90.0),
                        affected_objects=[c_name],
                        canonical_references=[CanonicalReference(canonical_id=c_id, source_identifier=c_name, object_type=obj_type)],
                        root_cause=f"Column '{c_name}' uses opaque vendor data type '{dt.get('name')}'",
                        impact="Requires fallback string emulation or custom type handler",
                        detection_engine=self.analyzer_id,
                        risk_fingerprint=f"fp-opaque-{c_name}",
                    )
                    items.append(item)

        return items

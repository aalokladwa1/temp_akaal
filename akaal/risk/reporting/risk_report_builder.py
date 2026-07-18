"""
Akaal — Risk Report Builder
===========================
Assembles final immutable RiskAssessmentModel artifacts from evaluated Risk pipeline results.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.risk_score import RiskScore
from akaal.risk.models.readiness import CutoverReadiness
from akaal.risk.models.complexity import MigrationComplexity
from akaal.risk.models.downtime import DowntimeEstimate
from akaal.risk.models.resource_estimate import ResourceEstimate
from akaal.risk.models.performance_prediction import PerformancePrediction
from akaal.risk.models.evidence import RiskEvidenceGraph
from akaal.risk.models.risk_dependency_graph import RiskDependencyGraph
from akaal.risk.models.risk_item import RiskItem
from akaal.risk.models.risk_manifest import RiskManifest
from akaal.risk.models.risk_assessment_model import RiskAssessmentModel
from akaal.risk.models.risk_trace import RiskExecutionTrace


class RiskReportBuilder:
    """Assembles final immutable RiskAssessmentModel."""

    @staticmethod
    def build_model(
        ctx: RiskContext,
        risk_score: RiskScore,
        readiness: CutoverReadiness,
        complexity: MigrationComplexity,
        downtime_estimate: DowntimeEstimate,
        resource_estimate: ResourceEstimate,
        performance_prediction: PerformancePrediction,
        evidence_graph: RiskEvidenceGraph,
        risk_dependency_graph: RiskDependencyGraph,
        risk_items: List[RiskItem],
        trace: RiskExecutionTrace,
    ) -> RiskAssessmentModel:
        manifest = RiskManifest(
            risk_schema_version=ctx.risk_schema_version,
            decoder_version=ctx.canonical_model.generator_version,
            canonical_schema_version=ctx.canonical_model.schema_version,
        )

        metadata = {
            "canonical_model_checksum": ctx.canonical_model.sha256_checksum,
            "correlation_id": ctx.correlation_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        items_dict = [item.to_dict() for item in risk_items]

        temp_dict = {
            "overall_risk_score": risk_score.to_dict(),
            "readiness": readiness.to_dict(),
            "complexity": complexity.to_dict(),
            "downtime_estimate": downtime_estimate.to_dict(),
            "resource_estimate": resource_estimate.to_dict(),
            "performance_prediction": performance_prediction.to_dict(),
            "risk_items": items_dict,
        }
        checksum_val = hashlib.sha256(json.dumps(temp_dict, default=str, sort_keys=True).encode("utf-8")).hexdigest()

        manifest.model_checksum = checksum_val

        return RiskAssessmentModel(
            sha256_checksum=checksum_val,
            metadata=metadata,
            manifest=manifest.to_dict(),
            overall_risk_score=risk_score.to_dict(),
            readiness=readiness.to_dict(),
            complexity=complexity.to_dict(),
            downtime_estimate=downtime_estimate.to_dict(),
            resource_estimate=resource_estimate.to_dict(),
            performance_prediction=performance_prediction.to_dict(),
            evidence_graph=evidence_graph.to_dict(),
            risk_dependency_graph=risk_dependency_graph.to_dict(),
            risk_items=items_dict,
            statistics={"total_risks_detected": len(risk_items)},
            execution_trace=trace.to_dict(),
        )

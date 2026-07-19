"""
Akaal — Advisor Serializer
==========================
Deterministic JSON, Dictionary, and Canonical serialization and deserialization for MigrationAdvisoryModel.
"""

import json
from typing import Any, Dict

from akaal.advisor.models.advisory_context import AdvisoryContext
from akaal.advisor.models.advisory_decision import AdvisoryDecision
from akaal.advisor.models.advisory_enums import (
    AdvisoryCategory,
    AdvisoryPriority,
    AdvisorySeverity,
)
from akaal.advisor.models.advisory_evidence import AdvisoryEvidence
from akaal.advisor.models.advisory_manifest import AdvisoryManifest
from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation
from akaal.advisor.models.advisory_trace import AdvisoryTrace
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel


class AdvisorSerializationError(Exception):
    """Exception raised for serialization / deserialization errors in Advisor Platform."""
    pass


class AdvisorSerializer:
    """Enterprise Serializer for MigrationAdvisoryModel objects."""

    @classmethod
    def to_dict(cls, model: MigrationAdvisoryModel) -> Dict[str, Any]:
        """Convert MigrationAdvisoryModel to standard dictionary."""
        if not isinstance(model, MigrationAdvisoryModel):
            raise AdvisorSerializationError(
                f"Expected MigrationAdvisoryModel, got {type(model).__name__}"
            )
        return model.to_dict()

    @classmethod
    def to_json(cls, model: MigrationAdvisoryModel, indent: int = 2) -> str:
        """Convert MigrationAdvisoryModel to deterministic JSON string."""
        if not isinstance(model, MigrationAdvisoryModel):
            raise AdvisorSerializationError(
                f"Expected MigrationAdvisoryModel, got {type(model).__name__}"
            )
        return model.to_json(indent=indent)

    @classmethod
    def to_canonical_dict(cls, model: MigrationAdvisoryModel) -> Dict[str, Any]:
        """Produce canonical dict representation (keys sorted deterministically)."""
        d = cls.to_dict(model)
        return json.loads(json.dumps(d, sort_keys=True, default=str))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MigrationAdvisoryModel:
        """Reconstruct MigrationAdvisoryModel from dictionary."""
        try:
            manifest_data = data.get("manifest", {})
            manifest = AdvisoryManifest(
                advisory_id=manifest_data.get("advisory_id", ""),
                plan_id=manifest_data.get("plan_id", ""),
                plan_checksum=manifest_data.get("plan_checksum", ""),
                total_recommendations=manifest_data.get("total_recommendations", 0),
                summary_by_category=dict(manifest_data.get("summary_by_category", {})),
                summary_by_severity=dict(manifest_data.get("summary_by_severity", {})),
                summary_by_priority=dict(manifest_data.get("summary_by_priority", {})),
                creation_timestamp=manifest_data.get("creation_timestamp", ""),
            )

            context_data = data.get("context", {})
            context = AdvisoryContext(
                environment=context_data.get("environment", "production"),
                database_type=context_data.get("database_type", "generic"),
                migration_type=context_data.get("migration_type", "online"),
                plan_id=context_data.get("plan_id", ""),
                target_tier=context_data.get("target_tier", "enterprise"),
                tags=tuple(context_data.get("tags", [])),
                metadata=dict(context_data.get("metadata", {})),
            )

            recs = []
            for r_data in data.get("recommendations", []):
                evidence_list = []
                for ev_data in r_data.get("evidence", []):
                    evidence_list.append(
                        AdvisoryEvidence(
                            source_component=ev_data.get("source_component", ""),
                            metric_name=ev_data.get("metric_name", ""),
                            observed_value=ev_data.get("observed_value"),
                            threshold_value=ev_data.get("threshold_value"),
                            evidence_details=dict(ev_data.get("evidence_details", {})),
                            references=tuple(ev_data.get("references", [])),
                        )
                    )

                dec_data = r_data.get("decision")
                decision = None
                if dec_data:
                    decision = AdvisoryDecision(
                        decision_id=dec_data.get("decision_id", ""),
                        recommendation_id=dec_data.get("recommendation_id", ""),
                        rationale=dec_data.get("rationale", ""),
                        impact_analysis=dec_data.get("impact_analysis", ""),
                        risk_mitigation=dec_data.get("risk_mitigation", ""),
                        alternatives_considered=tuple(dec_data.get("alternatives_considered", [])),
                        lineage=dict(dec_data.get("lineage", {})),
                    )

                category_str = r_data.get("category", "BEST_PRACTICE")
                severity_str = r_data.get("severity", "INFORMATIONAL")
                priority_str = r_data.get("priority", "P4")

                recs.append(
                    AdvisoryRecommendation(
                        recommendation_id=r_data.get("recommendation_id", ""),
                        title=r_data.get("title", ""),
                        category=AdvisoryCategory(category_str),
                        severity=AdvisorySeverity(severity_str),
                        priority=AdvisoryPriority(priority_str),
                        description=r_data.get("description", ""),
                        rationale=r_data.get("rationale", ""),
                        impact=r_data.get("impact", ""),
                        action_items=tuple(r_data.get("action_items", [])),
                        affected_nodes=tuple(r_data.get("affected_nodes", [])),
                        evidence=tuple(evidence_list),
                        decision=decision,
                        fingerprint=r_data.get("fingerprint", ""),
                        metadata=dict(r_data.get("metadata", {})),
                        tags=tuple(r_data.get("tags", [])),
                    )
                )

            trace_data = data.get("trace", {})
            trace = AdvisoryTrace(
                trace_id=trace_data.get("trace_id", ""),
                execution_duration_ms=float(trace_data.get("execution_duration_ms", 0.0)),
                analyzer_traces=tuple(dict(t) for t in trace_data.get("analyzer_traces", [])),
                lineage_graph=dict(trace_data.get("lineage_graph", {})),
                diagnostic_logs=tuple(trace_data.get("diagnostic_logs", [])),
            )

            return MigrationAdvisoryModel(
                schema_version=data.get("schema_version", "1.0.0"),
                model_version=data.get("model_version", "1.0.0"),
                generator_version=data.get("generator_version", "advisor-1.0.0"),
                model_signature=data.get("model_signature", "AKAAL-ADVISOR-SIG-V1"),
                sha256_checksum=data.get("sha256_checksum", ""),
                manifest=manifest,
                context=context,
                recommendations=tuple(recs),
                trace=trace,
                governance=dict(data.get("governance", {})),
                metadata=dict(data.get("metadata", {})),
                statistics=dict(data.get("statistics", {})),
            )
        except Exception as ex:
            raise AdvisorSerializationError(f"Failed to deserialize MigrationAdvisoryModel: {str(ex)}") from ex

    @classmethod
    def from_json(cls, json_str: str) -> MigrationAdvisoryModel:
        """Reconstruct MigrationAdvisoryModel from JSON string."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except Exception as ex:
            raise AdvisorSerializationError(f"Failed to parse JSON string: {str(ex)}") from ex

"""
AKAAL Enterprise Intelligence Platform — Serialization Subsystem
=================================================================
Lossless Python dict and JSON serializer/deserializer for canonical EnterpriseIntelligenceModel
artifacts with canonical key ordering and unknown field tolerance.
"""

import json
from typing import Any, Dict
from akaal.intelligence.models.agent_coordination_plan import AgentCoordinationPlan
from akaal.intelligence.models.enterprise_decision import EnterpriseDecision
from akaal.intelligence.models.enterprise_intelligence_enums import (
    DecisionPriority,
    ReadinessTier,
    RiskLevel,
    StrategyType,
)
from akaal.intelligence.models.enterprise_intelligence_manifest import EnterpriseIntelligenceManifest
from akaal.intelligence.models.enterprise_intelligence_model import EnterpriseIntelligenceModel
from akaal.intelligence.models.enterprise_intelligence_trace import EnterpriseIntelligenceTrace
from akaal.intelligence.models.enterprise_intelligence_version import EnterpriseIntelligenceVersionInfo
from akaal.intelligence.models.migration_simulation_result import MigrationSimulationResult
from akaal.intelligence.models.readiness_assessment import ReadinessAssessment
from akaal.intelligence.models.strategy_synthesis import StrategySynthesis


class EnterpriseIntelligenceSerializerError(Exception):
    """Exception raised for errors in EnterpriseIntelligenceSerializer operations."""
    pass


class EnterpriseIntelligenceSerializer:
    """
    Deterministic serializer for Platform 2 EnterpriseIntelligenceModel documents.
    """

    @staticmethod
    def to_dict(model: EnterpriseIntelligenceModel) -> Dict[str, Any]:
        """Converts model object to Python dictionary."""
        if not isinstance(model, EnterpriseIntelligenceModel):
            raise EnterpriseIntelligenceSerializerError(
                f"Expected EnterpriseIntelligenceModel, got {type(model).__name__}."
            )
        return model.to_dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EnterpriseIntelligenceModel:
        """
        Reconstructs EnterpriseIntelligenceModel from Python dictionary.
        Tolerates unknown future schema fields gracefully.
        """
        if not isinstance(data, dict):
            raise EnterpriseIntelligenceSerializerError(
                f"Expected dictionary payload, got {type(data).__name__}."
            )

        try:
            # Reconstruct VersionInfo
            v_data = data.get("version_info", {})
            version_info = EnterpriseIntelligenceVersionInfo(
                schema_version=v_data.get("schema_version", "1.0.0"),
                platform_version=v_data.get("platform_version", "1.0.0"),
                compatibility_flags=v_data.get("compatibility_flags", {}),
            )

            # Reconstruct Manifest
            m_data = data.get("manifest", {})
            manifest = EnterpriseIntelligenceManifest(
                advisory_model_id=m_data.get("advisory_model_id", ""),
                total_decisions=m_data.get("total_decisions", 0),
                critical_decisions_count=m_data.get("critical_decisions_count", 0),
                high_priority_decisions_count=m_data.get("high_priority_decisions_count", 0),
                readiness_score=float(m_data.get("readiness_score", 0.0)),
                simulated_downtime_p95_seconds=float(m_data.get("simulated_downtime_p95_seconds", 0.0)),
                generated_at_timestamp=m_data.get("generated_at_timestamp", ""),
                metadata=m_data.get("metadata", {}),
            )

            # Reconstruct Decisions
            decisions_list = []
            for d in data.get("decisions", []):
                decisions_list.append(
                    EnterpriseDecision(
                        decision_id=d.get("decision_id", ""),
                        title=d.get("title", ""),
                        category=d.get("category", ""),
                        priority=DecisionPriority(d.get("priority", DecisionPriority.MEDIUM.value)),
                        risk_level=RiskLevel(d.get("risk_level", RiskLevel.MEDIUM.value)),
                        description=d.get("description", ""),
                        rationale=d.get("rationale", ""),
                        strategic_impact=d.get("strategic_impact", ""),
                        confidence_score=float(d.get("confidence_score", 0.0)),
                        action_items=tuple(d.get("action_items", ())),
                        trade_offs=tuple(d.get("trade_offs", ())),
                        affected_components=tuple(d.get("affected_components", ())),
                        evidence_pointers=tuple(d.get("evidence_pointers", ())),
                        metadata=d.get("metadata", {}),
                    )
                )

            # Reconstruct Strategy
            s_data = data.get("strategy", {})
            strategy = StrategySynthesis(
                strategy_id=s_data.get("strategy_id", ""),
                strategy_type=StrategyType(s_data.get("strategy_type", StrategyType.BALANCED_STAGE_BY_STAGE.value)),
                primary_objective=s_data.get("primary_objective", ""),
                recommended_execution_mode=s_data.get("recommended_execution_mode", ""),
                estimated_total_duration_seconds=float(s_data.get("estimated_total_duration_seconds", 0.0)),
                max_recommended_parallelism=int(s_data.get("max_recommended_parallelism", 1)),
                key_assumptions=tuple(s_data.get("key_assumptions", ())),
                strategic_advantages=tuple(s_data.get("strategic_advantages", ())),
                identified_constraints=tuple(s_data.get("identified_constraints", ())),
                mitigation_guidelines=tuple(s_data.get("mitigation_guidelines", ())),
                metadata=s_data.get("metadata", {}),
            )

            # Reconstruct Simulation
            sim_data = data.get("simulation", {})
            simulation = MigrationSimulationResult(
                simulation_id=sim_data.get("simulation_id", ""),
                projected_downtime_seconds_min=float(sim_data.get("projected_downtime_seconds_min", 0.0)),
                projected_downtime_seconds_max=float(sim_data.get("projected_downtime_seconds_max", 0.0)),
                projected_downtime_seconds_p95=float(sim_data.get("projected_downtime_seconds_p95", 0.0)),
                projected_total_duration_seconds=float(sim_data.get("projected_total_duration_seconds", 0.0)),
                estimated_throughput_records_per_sec=float(sim_data.get("estimated_throughput_records_per_sec", 0.0)),
                peak_memory_mb_estimate=float(sim_data.get("peak_memory_mb_estimate", 0.0)),
                peak_cpu_cores_estimate=float(sim_data.get("peak_cpu_cores_estimate", 0.0)),
                failure_probability=float(sim_data.get("failure_probability", 0.0)),
                bottleneck_stages=tuple(sim_data.get("bottleneck_stages", ())),
                simulated_risk_factors=tuple(sim_data.get("simulated_risk_factors", ())),
                metadata=sim_data.get("metadata", {}),
            )

            # Reconstruct Readiness
            r_data = data.get("readiness", {})
            readiness = ReadinessAssessment(
                assessment_id=r_data.get("assessment_id", ""),
                overall_readiness_score=float(r_data.get("overall_readiness_score", 0.0)),
                tier=ReadinessTier(r_data.get("tier", ReadinessTier.NOT_READY.value)),
                schema_readiness_score=float(r_data.get("schema_readiness_score", 0.0)),
                data_readiness_score=float(r_data.get("data_readiness_score", 0.0)),
                hardware_readiness_score=float(r_data.get("hardware_readiness_score", 0.0)),
                operational_readiness_score=float(r_data.get("operational_readiness_score", 0.0)),
                critical_blockers=tuple(r_data.get("critical_blockers", ())),
                warnings=tuple(r_data.get("warnings", ())),
                remediation_steps=tuple(r_data.get("remediation_steps", ())),
                metadata=r_data.get("metadata", {}),
            )

            # Reconstruct AgentCoordination
            a_data = data.get("agent_coordination", {})
            agent_coordination = AgentCoordinationPlan(
                plan_id=a_data.get("plan_id", ""),
                total_recommended_agents=int(a_data.get("total_recommended_agents", 1)),
                primary_region=a_data.get("primary_region", ""),
                secondary_regions=tuple(a_data.get("secondary_regions", ())),
                worker_distribution=a_data.get("worker_distribution", {}),
                failover_nodes=tuple(a_data.get("failover_nodes", ())),
                coordination_notes=tuple(a_data.get("coordination_notes", ())),
                metadata=a_data.get("metadata", {}),
            )

            # Reconstruct Trace
            t_data = data.get("trace", {})
            trace = EnterpriseIntelligenceTrace(
                trace_id=t_data.get("trace_id", ""),
                total_execution_duration_ms=float(t_data.get("total_execution_duration_ms", 0.0)),
                analyzer_durations_ms=t_data.get("analyzer_durations_ms", {}),
                decision_graph_duration_ms=float(t_data.get("decision_graph_duration_ms", 0.0)),
                evaluation_logs=tuple(t_data.get("evaluation_logs", ())),
                metadata=t_data.get("metadata", {}),
            )

            return EnterpriseIntelligenceModel(
                model_id=data.get("model_id", ""),
                advisory_model_id=data.get("advisory_model_id", ""),
                version_info=version_info,
                manifest=manifest,
                decisions=tuple(decisions_list),
                strategy=strategy,
                simulation=simulation,
                readiness=readiness,
                agent_coordination=agent_coordination,
                trace=trace,
                checksum=data.get("checksum", ""),
                metadata=data.get("metadata", {}),
            )

        except Exception as ex:
            raise EnterpriseIntelligenceSerializerError(
                f"Failed to deserialize dictionary into EnterpriseIntelligenceModel: {ex}"
            ) from ex

    @classmethod
    def to_json(cls, model: EnterpriseIntelligenceModel, indent: int = 2) -> str:
        """Serializes model to JSON string with canonical key sorting."""
        d_dict = cls.to_dict(model)
        try:
            return json.dumps(d_dict, indent=indent, sort_keys=True)
        except Exception as ex:
            raise EnterpriseIntelligenceSerializerError(f"Failed to serialize model to JSON: {ex}") from ex

    @classmethod
    def from_json(cls, json_str: str) -> EnterpriseIntelligenceModel:
        """Deserializes JSON string into EnterpriseIntelligenceModel."""
        if not isinstance(json_str, str) or not json_str.strip():
            raise EnterpriseIntelligenceSerializerError("JSON string input cannot be empty.")

        try:
            data = json.loads(json_str)
        except Exception as ex:
            raise EnterpriseIntelligenceSerializerError(f"Invalid JSON payload: {ex}") from ex

        return cls.from_dict(data)

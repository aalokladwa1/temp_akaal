"""
Akaal — Planner Serializer
============================
Deterministic JSON and versioned export/import serializer for MigrationExecutionPlan.
"""

import json
from akaal.planner.models.migration_execution_plan import MigrationExecutionPlan


class PlannerSerializer:
    """Deterministic serializer for MigrationExecutionPlan artifacts."""

    @staticmethod
    def serialize_json(plan: MigrationExecutionPlan, indent: int = 2) -> str:
        return json.dumps(plan.to_dict(), default=str, sort_keys=True, indent=indent)

    @staticmethod
    def deserialize_json(json_str: str) -> MigrationExecutionPlan:
        d = json.loads(json_str)
        return MigrationExecutionPlan(
            schema_version=d.get("schema_version", "1.0.0"),
            model_version=d.get("model_version", "1.0.0"),
            generator_version=d.get("generator_version", "planner-1.0.0"),
            model_signature=d.get("model_signature", "AKAAL-PLANNER-SIG-V1"),
            sha256_checksum=d.get("sha256_checksum", ""),
            metadata=d.get("metadata", {}),
            manifest=d.get("manifest", {}),
            version_info=d.get("version_info", {}),
            strategy=d.get("strategy", {}),
            constraints=d.get("constraints", {}),
            execution_graph=d.get("execution_graph", {}),
            execution_stages=d.get("execution_stages", []),
            execution_sequence=d.get("execution_sequence", {}),
            execution_timeline=d.get("execution_timeline", {}),
            dependency_graph=d.get("dependency_graph", {}),
            parallel_strategy=d.get("parallel_strategy", {}),
            checkpoint_plan=d.get("checkpoint_plan", {}),
            rollback_plan=d.get("rollback_plan", {}),
            resource_schedule=d.get("resource_schedule", {}),
            resource_allocation_graph=d.get("resource_allocation_graph", {}),
            cutover_plan=d.get("cutover_plan", {}),
            planning_decisions=d.get("planning_decisions", []),
            evidence_graph=d.get("evidence_graph", {}),
            statistics=d.get("statistics", {}),
            planning_trace=d.get("planning_trace", {}),
            diagnostics=d.get("diagnostics", []),
        )

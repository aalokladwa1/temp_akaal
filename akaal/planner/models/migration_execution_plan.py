"""
Akaal — Migration Execution Plan
==================================
The single canonical, immutable, versioned, checksum-protected output artifact produced by Planner Platform.
Consumed downstream by Advisor, Enterprise Intelligence, Mission Control, and Dashboards.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class MigrationExecutionPlan:
    """
    Immutable, versioned MigrationExecutionPlan artifact.
    Single public output produced by Planner Platform.
    """
    schema_version: str = "1.0.0"
    model_version: str = "1.0.0"
    generator_version: str = "planner-1.0.0"
    model_signature: str = "AKAAL-PLANNER-SIG-V1"
    sha256_checksum: str = ""

    metadata: Dict[str, Any] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)
    version_info: Dict[str, Any] = field(default_factory=dict)
    strategy: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    execution_graph: Dict[str, Any] = field(default_factory=dict)
    execution_stages: List[Dict[str, Any]] = field(default_factory=list)
    execution_sequence: Dict[str, Any] = field(default_factory=dict)
    execution_timeline: Dict[str, Any] = field(default_factory=dict)
    dependency_graph: Dict[str, Any] = field(default_factory=dict)
    parallel_strategy: Dict[str, Any] = field(default_factory=dict)
    checkpoint_plan: Dict[str, Any] = field(default_factory=dict)
    rollback_plan: Dict[str, Any] = field(default_factory=dict)
    resource_schedule: Dict[str, Any] = field(default_factory=dict)
    resource_allocation_graph: Dict[str, Any] = field(default_factory=dict)
    cutover_plan: Dict[str, Any] = field(default_factory=dict)
    planning_decisions: List[Dict[str, Any]] = field(default_factory=list)
    evidence_graph: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    planning_trace: Dict[str, Any] = field(default_factory=dict)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "schema_version": self.schema_version,
            "model_version": self.model_version,
            "generator_version": self.generator_version,
            "model_signature": self.model_signature,
            "sha256_checksum": self.sha256_checksum,
            "metadata": self.metadata,
            "manifest": self.manifest,
            "version_info": self.version_info,
            "strategy": self.strategy,
            "constraints": self.constraints,
            "execution_graph": self.execution_graph,
            "execution_stages": self.execution_stages,
            "execution_sequence": self.execution_sequence,
            "execution_timeline": self.execution_timeline,
            "dependency_graph": self.dependency_graph,
            "parallel_strategy": self.parallel_strategy,
            "checkpoint_plan": self.checkpoint_plan,
            "rollback_plan": self.rollback_plan,
            "resource_schedule": self.resource_schedule,
            "resource_allocation_graph": self.resource_allocation_graph,
            "cutover_plan": self.cutover_plan,
            "planning_decisions": self.planning_decisions,
            "evidence_graph": self.evidence_graph,
            "statistics": self.statistics,
            "planning_trace": self.planning_trace,
            "diagnostics": self.diagnostics,
        }
        if not res["sha256_checksum"]:
            stable = {
                "strategy": self.strategy,
                "execution_graph": self.execution_graph,
                "execution_sequence": self.execution_sequence,
                "checkpoint_plan": self.checkpoint_plan,
                "rollback_plan": self.rollback_plan,
                "cutover_plan": self.cutover_plan,
            }
            res["sha256_checksum"] = hashlib.sha256(
                json.dumps(stable, default=str, sort_keys=True).encode("utf-8")
            ).hexdigest()
        return res

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

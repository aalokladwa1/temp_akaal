"""
Akaal — Rulebook Platform Public API
====================================
Public API for enterprise policy decision making. Converts DiscoveryReport to MigrationRuleSet.
"""

import time
import logging
from typing import Any, Dict, Optional, Union

from akaal.scout.models.discovery_report import DiscoveryReport
from akaal.rulebook.models.rule_evaluation_context import RuleEvaluationContext
from akaal.rulebook.models.rule_execution_trace import RuleExecutionTrace, TraceStep
from akaal.rulebook.models.migration_ruleset import MigrationRuleSet
from akaal.rulebook.models.simulation_report import SimulationReport
from akaal.rulebook.registry.rule_registry import RuleRegistry
from akaal.rulebook.registry.rule_pack_registry import RulePackRegistry
from akaal.rulebook.cache.resolution_cache import RuleResolutionCache
from akaal.rulebook.metrics.rulebook_metrics import RulebookMetrics

from akaal.rulebook.engine.rule_resolution_engine import RuleResolutionEngine
from akaal.rulebook.engine.validation_engine import ValidationEngine
from akaal.rulebook.engine.priority_engine import PriorityEngine
from akaal.rulebook.engine.conflict_engine import ConflictEngine
from akaal.rulebook.engine.inheritance_engine import InheritanceEngine
from akaal.rulebook.engine.simulation_engine import SimulationEngine
from akaal.rulebook.reporting.ruleset_report_builder import RuleSetReportBuilder

logger = logging.getLogger("akaal.rulebook")


class RulebookPlatform:
    """
    Public entry point for Rulebook Platform.
    Converts DiscoveryReport into immutable MigrationRuleSet.
    Contains zero SQL generation or migration execution.
    """

    _rule_registry: Optional[RuleRegistry] = None
    _pack_registry: Optional[RulePackRegistry] = None
    _cache: Optional[RuleResolutionCache] = None

    @classmethod
    def get_rule_registry(cls) -> RuleRegistry:
        if cls._rule_registry is None:
            cls._rule_registry = RuleRegistry()
            # Register rules from default packs
            pack_reg = cls.get_pack_registry()
            for pack_info in pack_reg.list_packs():
                provider = pack_reg.get_provider(pack_info["provider_id"])
                if provider:
                    for rule in provider.rules():
                        cls._rule_registry.register(rule)
        return cls._rule_registry

    @classmethod
    def get_pack_registry(cls) -> RulePackRegistry:
        if cls._pack_registry is None:
            cls._pack_registry = RulePackRegistry(auto_register_defaults=True)
        return cls._pack_registry

    @classmethod
    def get_cache(cls) -> RuleResolutionCache:
        if cls._cache is None:
            cls._cache = RuleResolutionCache()
        return cls._cache

    @classmethod
    def generate_ruleset(
        cls,
        discovery_report: DiscoveryReport,
        target_engine: str = "POSTGRESQL",
        migration_config: Optional[Any] = None,
        org_policies: Optional[Dict[str, Any]] = None,
    ) -> MigrationRuleSet:
        t0 = time.time()
        rule_reg = cls.get_rule_registry()
        pack_reg = cls.get_pack_registry()
        cache = cls.get_cache()
        metrics = RulebookMetrics()

        ctx = RuleEvaluationContext(
            discovery_report=discovery_report,
            target_engine=target_engine,
            migration_config=migration_config,
            org_policies=org_policies or {},
            rule_registry_ref=rule_reg,
            rule_pack_registry_ref=pack_reg,
            simulation_mode=False,
        )

        trace = RuleExecutionTrace(correlation_id=ctx.correlation_id)

        # 1. Dependency Graph & Resolution
        res_engine = RuleResolutionEngine()
        candidates = res_engine.resolve_candidate_rules(ctx)

        # Sort by Topological Graph Order
        ordered_rules = rule_reg.graph.topological_sort()
        candidate_ids = {r.rule_id for r in candidates}
        resolved_rules = [r for r in ordered_rules if r.rule_id in candidate_ids]

        trace.add_step(TraceStep(
            evaluation_order=1,
            engine_name="RuleResolutionEngine",
            rule_id="DEPENDENCY_SORT",
            decision="RESOLVED",
            applied_reason=f"Resolved {len(resolved_rules)} candidate rules in DAG topological order.",
        ))

        # 2. Validation Engine
        val_engine = ValidationEngine()
        valid_rules, invalid_rules, val_reasons = val_engine.validate_rules(resolved_rules, ctx)

        trace.add_step(TraceStep(
            evaluation_order=2,
            engine_name="ValidationEngine",
            rule_id="VALIDATION",
            decision="VALIDATED",
            applied_reason=f"Validated {len(valid_rules)} rules. Skipped {len(invalid_rules)} invalid rules.",
        ))

        # 3. Priority Engine
        prio_engine = PriorityEngine()
        prioritized_rules = prio_engine.prioritize_rules(valid_rules)

        trace.add_step(TraceStep(
            evaluation_order=3,
            engine_name="PriorityEngine",
            rule_id="PRIORITIZATION",
            decision="PRIORITIZED",
            applied_reason="Prioritized rules based on scope precedence & priority score.",
        ))

        # 4. Conflict Engine
        conf_engine = ConflictEngine()
        conflict_free_rules, diagnostics = conf_engine.detect_conflicts(prioritized_rules)

        trace.add_step(TraceStep(
            evaluation_order=4,
            engine_name="ConflictEngine",
            rule_id="CONFLICT_DETECTION",
            decision="CLEARED",
            applied_reason=f"Detected {len(diagnostics)} rule conflicts.",
        ))

        # 5. Inheritance Engine
        inh_engine = InheritanceEngine()
        evaluation_results, inheritance_summary = inh_engine.resolve_inheritance(conflict_free_rules)

        trace.add_step(TraceStep(
            evaluation_order=5,
            engine_name="InheritanceEngine",
            rule_id="INHERITANCE_RESOLUTION",
            decision="RESOLVED",
            applied_reason="Evaluated 8-level policy hierarchy overrides.",
        ))

        # 6. Report Assembler
        ruleset = RuleSetReportBuilder.build_ruleset(
            ctx=ctx,
            results=evaluation_results,
            inheritance_summary=inheritance_summary,
            diagnostics=diagnostics,
            trace=trace,
        )

        t1 = time.time()
        metrics.record_resolution_time((t1 - t0) * 1000.0)

        return ruleset

    @classmethod
    def simulate(
        cls,
        discovery_report: DiscoveryReport,
        target_engine: str = "POSTGRESQL",
        migration_config: Optional[Any] = None,
        org_policies: Optional[Dict[str, Any]] = None,
    ) -> SimulationReport:
        rule_reg = cls.get_rule_registry()
        pack_reg = cls.get_pack_registry()

        ctx = RuleEvaluationContext(
            discovery_report=discovery_report,
            target_engine=target_engine,
            migration_config=migration_config,
            org_policies=org_policies or {},
            rule_registry_ref=rule_reg,
            rule_pack_registry_ref=pack_reg,
            simulation_mode=True,
        )

        trace = RuleExecutionTrace(correlation_id=ctx.correlation_id)

        res_engine = RuleResolutionEngine()
        candidates = res_engine.resolve_candidate_rules(ctx)

        ordered_rules = rule_reg.graph.topological_sort()
        candidate_ids = {r.rule_id for r in candidates}
        resolved_rules = [r for r in ordered_rules if r.rule_id in candidate_ids]

        val_engine = ValidationEngine()
        valid_rules, invalid_rules, val_reasons = val_engine.validate_rules(resolved_rules, ctx)

        prio_engine = PriorityEngine()
        prioritized_rules = prio_engine.prioritize_rules(valid_rules)

        conf_engine = ConflictEngine()
        conflict_free_rules, diagnostics = conf_engine.detect_conflicts(prioritized_rules)

        inh_engine = InheritanceEngine()
        evaluation_results, inheritance_summary = inh_engine.resolve_inheritance(conflict_free_rules)

        sim_engine = SimulationEngine()
        return sim_engine.simulate(ctx, evaluation_results, diagnostics, trace)


def generate_ruleset(
    discovery_report: DiscoveryReport,
    target_engine: str = "POSTGRESQL",
    migration_config: Optional[Any] = None,
    org_policies: Optional[Dict[str, Any]] = None,
) -> MigrationRuleSet:
    """Top-level function for Rulebook ruleset generation."""
    return RulebookPlatform.generate_ruleset(
        discovery_report=discovery_report,
        target_engine=target_engine,
        migration_config=migration_config,
        org_policies=org_policies,
    )

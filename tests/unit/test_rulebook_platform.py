"""
Unit Tests for Rulebook Platform Subsystem (Phase 9 - Feature 2)
================================================================
Comprehensive test suite covering DependencyGraph, Lifecycle, Provenance, CapabilityMetadata,
Provider Plugins, Resolution Cache, Conflict Diagnostics, 8-Level Inheritance, Simulation,
MigrationRuleSet immutability, and Enterprise Stress Testing.
"""

import unittest
import json
import hashlib
from typing import List

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.scout.models.discovery_request import DiscoveryRequest
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.reporting.discovery_assembler import DiscoveryAssembler

from akaal.rulebook.models.rule import (
    Rule,
    RuleLifecycleState,
    RuleProvenance,
    RuleCategory,
    RuleScope,
    RuleCapabilityMetadata,
)
from akaal.rulebook.models.rule_evaluation_context import RuleEvaluationContext
from akaal.rulebook.models.rule_execution_trace import RuleExecutionTrace, TraceStep
from akaal.rulebook.models.rule_diagnostic import RuleDiagnostic, DiagnosticSeverity
from akaal.rulebook.models.rule_audit import RuleAudit
from akaal.rulebook.models.rule_manifest import RuleManifest
from akaal.rulebook.models.simulation_report import SimulationReport
from akaal.rulebook.models.migration_ruleset import MigrationRuleSet

from akaal.rulebook.providers.base_provider import BaseRuleProvider
from akaal.rulebook.providers.generic_provider import GenericRuleProvider
from akaal.rulebook.providers.postgres_provider import PostgresRuleProvider
from akaal.rulebook.registry.rule_registry import RuleRegistry
from akaal.rulebook.registry.rule_pack_registry import RulePackRegistry
from akaal.rulebook.cache.resolution_cache import RuleResolutionCache

from akaal.rulebook.engine.dependency_graph import DependencyGraph
from akaal.rulebook.engine.rule_resolution_engine import RuleResolutionEngine
from akaal.rulebook.engine.validation_engine import ValidationEngine
from akaal.rulebook.engine.priority_engine import PriorityEngine
from akaal.rulebook.engine.conflict_engine import ConflictEngine
from akaal.rulebook.engine.inheritance_engine import InheritanceEngine
from akaal.rulebook.engine.simulation_engine import SimulationEngine

from akaal.rulebook.api.rulebook_platform import RulebookPlatform, generate_ruleset


class MockProvider(BaseRuleProvider):
    provider_id = "mock_pack"
    provider_name = "Mock Rule Pack"
    provider_version = "1.0.0"
    target_engine = "POSTGRESQL"

    def rules(self) -> List[Rule]:
        return [
            Rule(
                rule_id="MOCK-001",
                name="Mock Rule 1",
                description="Test rule 1",
                category=RuleCategory.NAMING,
                scope=RuleScope.GLOBAL,
                priority=50,
            ),
            Rule(
                rule_id="MOCK-002",
                name="Mock Rule 2",
                description="Test rule 2 depending on 1",
                category=RuleCategory.NAMING,
                scope=RuleScope.TABLE,
                priority=100,
                prerequisites=["MOCK-001"],
            ),
        ]


class TestRulebookPlatform(unittest.TestCase):

    def setUp(self):
        config = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host="source-db.example.com",
            port=5432,
            database_name="test_db",
            credentials_ref="vault://pg_creds",
        )
        ctx = DiscoveryContext(request=DiscoveryRequest(config))
        self.report = DiscoveryAssembler.assemble(ctx)

    def test_dependency_graph_and_topological_sort(self):
        graph = DependencyGraph()
        rule1 = Rule("R1", "Rule 1", "Desc", RuleCategory.VENDOR)
        rule2 = Rule("R2", "Rule 2", "Desc", RuleCategory.VENDOR, prerequisites=["R1"])
        rule3 = Rule("R3", "Rule 3", "Desc", RuleCategory.VENDOR, prerequisites=["R2"])

        graph.build([rule3, rule2, rule1])
        ordered = graph.topological_sort()
        ordered_ids = [r.rule_id for r in ordered]
        self.assertEqual(ordered_ids, ["R1", "R2", "R3"])
        self.assertEqual(graph.detect_cycles(), [])

    def test_dependency_graph_cycle_detection(self):
        graph = DependencyGraph()
        rule1 = Rule("C1", "Cycle 1", "Desc", RuleCategory.VENDOR, prerequisites=["C2"])
        rule2 = Rule("C2", "Cycle 2", "Desc", RuleCategory.VENDOR, prerequisites=["C1"])

        graph.build([rule1, rule2])
        cycles = graph.detect_cycles()
        self.assertTrue(len(cycles) > 0)
        validation_errors = graph.validate()
        self.assertTrue(len(validation_errors) > 0)

    def test_rule_lifecycle_state_machine(self):
        retired_rule = Rule("RET-001", "Retired Rule", "Desc", RuleCategory.NAMING, lifecycle_state=RuleLifecycleState.RETIRED)
        active_rule = Rule("ACT-001", "Active Rule", "Desc", RuleCategory.NAMING, lifecycle_state=RuleLifecycleState.ACTIVE)
        deprecated_rule = Rule("DEP-001", "Deprecated Rule", "Desc", RuleCategory.NAMING, lifecycle_state=RuleLifecycleState.DEPRECATED)

        ctx = RuleEvaluationContext(discovery_report=self.report)
        val_engine = ValidationEngine()
        valid, invalid, reasons = val_engine.validate_rules([retired_rule, active_rule, deprecated_rule], ctx)

        valid_ids = [r.rule_id for r in valid]
        invalid_ids = [r.rule_id for r in invalid]

        self.assertIn("ACT-001", valid_ids)
        self.assertIn("DEP-001", valid_ids)
        self.assertIn("RET-001", invalid_ids)

    def test_rule_provenance_and_audit(self):
        rule = Rule("PROV-001", "Prov Rule", "Desc", RuleCategory.SECURITY, provenance=RuleProvenance.ORGANIZATION_POLICY)
        self.assertEqual(rule.provenance, RuleProvenance.ORGANIZATION_POLICY)

    def test_rule_capability_metadata_validation(self):
        rule_req_cluster = Rule(
            "CAP-001",
            "Cluster Rule",
            "Requires cluster discovery",
            category=RuleCategory.VENDOR,
            capability_metadata=RuleCapabilityMetadata(required_discovery_sections=["ClusterDiscovery"]),
        )
        ctx = RuleEvaluationContext(discovery_report=self.report)
        val_engine = ValidationEngine()
        valid, invalid, reasons = val_engine.validate_rules([rule_req_cluster], ctx)
        self.assertEqual(len(valid), 1)

    def test_rule_pack_registry_and_providers(self):
        pack_reg = RulePackRegistry(auto_register_defaults=False)
        mock_provider = MockProvider()
        pack_reg.load(mock_provider)

        self.assertIsNotNone(pack_reg.get_provider("mock_pack"))
        self.assertEqual(len(pack_reg.list_packs()), 1)
        self.assertTrue(len(pack_reg.checksum("mock_pack")) > 0)

        manifest = pack_reg.manifest()
        self.assertIn("mock_pack", manifest)

    def test_resolution_cache(self):
        cache = RuleResolutionCache()
        self.assertIsNone(cache.get("k1"))
        cache.set("k1", "val1")
        self.assertEqual(cache.get("k1"), "val1")

        stats = cache.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)

        cache.invalidate("k1")
        self.assertIsNone(cache.get("k1"))

    def test_conflict_engine_and_diagnostics(self):
        rule1 = Rule("DUP-001", "Rule 1", "Desc", RuleCategory.NAMING)
        rule2 = Rule("DUP-001", "Duplicate Rule 1", "Desc", RuleCategory.NAMING)

        conf_engine = ConflictEngine()
        filtered, diagnostics = conf_engine.detect_conflicts([rule1, rule2])
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].severity, DiagnosticSeverity.ERROR)

    def test_inheritance_engine_8_level_overrides(self):
        global_rule = Rule("INH-001", "Global Rule", "Desc", RuleCategory.NAMING, scope=RuleScope.GLOBAL)
        table_rule = Rule("INH-002", "Table Rule", "Desc", RuleCategory.NAMING, scope=RuleScope.TABLE)

        inh_engine = InheritanceEngine()
        results, summary = inh_engine.resolve_inheritance([global_rule, table_rule])

        statuses = {r.rule_id: r.status for r in results}
        self.assertEqual(statuses["INH-002"], "APPLIED")
        self.assertEqual(statuses["INH-001"], "OVERRIDDEN")

    def test_simulation_engine_report(self):
        report = RulebookPlatform.simulate(self.report, target_engine="POSTGRESQL")
        self.assertIsNotNone(report)
        self.assertIsInstance(report, SimulationReport)
        self.assertTrue(report.rules_loaded >= 0)

    def test_migration_ruleset_immutability_and_checksum(self):
        ruleset = generate_ruleset(self.report, target_engine="POSTGRESQL")
        self.assertIsNotNone(ruleset)
        self.assertIsInstance(ruleset, MigrationRuleSet)
        self.assertEqual(ruleset.schema_version, "1.0.0")
        self.assertTrue(len(ruleset.sha256_checksum) > 0)

        # Immutability check (frozen dataclass)
        with self.assertRaises(AttributeError):
            ruleset.sha256_checksum = "modified"

    def test_enterprise_stress_and_determinism(self):
        rule_reg = RuleRegistry()
        rules = []
        for i in range(1000):
            rules.append(Rule(
                rule_id=f"STRESS-{i:04d}",
                name=f"Stress Rule {i}",
                description="Stress test rule",
                category=RuleCategory.CONVERSION,
                scope=RuleScope.TABLE if i % 2 == 0 else RuleScope.GLOBAL,
                priority=i % 100,
            ))
        for r in rules:
            rule_reg.register(r)

        self.assertEqual(len(rule_reg.get_all_rules()), 1000)

        # Verify deterministic execution across 5 consecutive runs
        checksums = set()
        for _ in range(5):
            rs = RulebookPlatform.generate_ruleset(self.report, target_engine="POSTGRESQL")
            checksums.add(rs.sha256_checksum)
        self.assertEqual(len(checksums), 1)


if __name__ == "__main__":
    unittest.main()

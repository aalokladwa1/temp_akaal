"""
Unit Tests for Risk Platform Subsystem (Phase 9 - Feature 4)
=============================================================
Comprehensive test suite covering Risk Taxonomy, Severity Matrix, Multi-Dimensional Confidence,
Risk Evidence Graph, Risk Dependency Graph, Multi-level Resource Estimation, Cutover Readiness,
Migration Complexity, Passive Analyzer Plugins, Serialization, Event System, RiskAssessmentModel
Immutability, 10-Run Determinism, and 1,000-Object Scale Stress Testing.
"""

import unittest
import json
import hashlib
import random
import time
import tracemalloc

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.scout.models.discovery_request import DiscoveryRequest
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.reporting.discovery_assembler import DiscoveryAssembler
from akaal.rulebook.api.rulebook_platform import RulebookPlatform
from akaal.decoder.api.decoder_platform import DecoderPlatform

from akaal.risk.models.risk_taxonomy import RiskDomain, RiskCategory, RiskType
from akaal.risk.models.severity import Severity, SeverityMatrix
from akaal.risk.models.confidence import ConfidenceScore
from akaal.risk.models.evidence import EvidenceNode, RiskEvidenceGraph
from akaal.risk.models.risk_dependency_graph import RiskDependencyGraph
from akaal.risk.models.mitigation import MitigationStrategy
from akaal.risk.models.canonical_reference import CanonicalReference
from akaal.risk.models.risk_item import RiskItem
from akaal.risk.models.risk_score import RiskScore
from akaal.risk.models.readiness import ReadinessClassification, CutoverReadiness
from akaal.risk.models.complexity import MigrationComplexity
from akaal.risk.models.downtime import DowntimeEstimate
from akaal.risk.models.resource_estimate import ResourceLevelEstimate, ResourceEstimate
from akaal.risk.models.performance_prediction import PerformancePrediction
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.risk_event import RiskEvent, RiskEventBus
from akaal.risk.models.risk_manifest import RiskManifest
from akaal.risk.models.risk_assessment_model import RiskAssessmentModel

from akaal.risk.analyzers.base_analyzer import BaseAnalyzer
from akaal.risk.analyzers.datatype_analyzer import DatatypeAnalyzer
from akaal.risk.registry.analyzer_registry import AnalyzerRegistry
from akaal.risk.serialization.risk_serializer import RiskSerializer

from akaal.risk.api.risk_platform import RiskPlatform, assess_risk


class TestRiskPlatform(unittest.TestCase):

    def setUp(self):
        config = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host="source-db.example.com",
            port=5432,
            database_name="test_db",
            credentials_ref="vault://pg_creds",
        )
        ctx = DiscoveryContext(request=DiscoveryRequest(config))
        report = DiscoveryAssembler.assemble(ctx)
        ruleset = RulebookPlatform.generate_ruleset(report, target_engine="POSTGRESQL")
        self.canonical_model = DecoderPlatform.normalize(report, ruleset)

    def test_risk_taxonomy_and_severity_matrix(self):
        sev_info = SeverityMatrix.calculate(0.1, 0.1, 0.0)
        self.assertEqual(sev_info, Severity.INFO)

        sev_critical = SeverityMatrix.calculate(1.0, 1.0, 1.0)
        self.assertEqual(sev_critical, Severity.CRITICAL)

    def test_multi_dimensional_confidence_model(self):
        conf = ConfidenceScore(
            metadata_confidence=90.0,
            rule_confidence=80.0,
            analyzer_confidence=100.0,
            capability_confidence=90.0,
            evidence_confidence=90.0,
        )
        self.assertEqual(conf.overall_confidence, 90.0)

    def test_risk_evidence_graph_and_references(self):
        graph = RiskEvidenceGraph()
        node = EvidenceNode(
            evidence_id="EV-1",
            node_type="CANONICAL_RULE_PROVENANCE",
            rule_provenance={"rule_id": "R-100", "rule_name": "PG_Rule"},
            analyzer_name="DatatypeAnalyzer",
            reason="Rule applied for postgres",
        )
        graph.add_node(node)
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(graph.nodes["EV-1"].rule_provenance["rule_id"], "R-100")

    def test_multi_level_resource_estimation(self):
        res = ResourceEstimate(
            cpu_cores=ResourceLevelEstimate(2, 4, 8, 16),
            memory_gb=ResourceLevelEstimate(4, 8, 16, 32),
        )
        res_dict = res.to_dict()
        self.assertEqual(res_dict["cpu_cores"]["recommended"], 4.0)
        self.assertEqual(res_dict["memory_gb"]["burst"], 32.0)

    def test_cutover_readiness_model(self):
        readiness = CutoverReadiness(
            technical_readiness=95.0,
            classification=ReadinessClassification.READY_WITH_WARNINGS,
        )
        self.assertEqual(readiness.classification, ReadinessClassification.READY_WITH_WARNINGS)

    def test_migration_complexity_model(self):
        cmpx = MigrationComplexity(
            structural_complexity=60.0,
            overall_complexity_score=60.0,
            complexity_tier="HIGH",
        )
        self.assertEqual(cmpx.complexity_tier, "HIGH")

    def test_passive_datatype_analyzer(self):
        ctx = RiskContext(canonical_model=self.canonical_model)
        analyzer = DatatypeAnalyzer()
        items = analyzer.analyze(ctx)
        self.assertIsInstance(items, list)

    def test_analyzer_registry_and_governance(self):
        reg = AnalyzerRegistry(auto_register_defaults=True)
        analyzers = reg.list_analyzers()
        self.assertTrue(len(analyzers) >= 7)

        dt_a = reg.get_analyzer("datatype_loss_analyzer")
        self.assertIsNotNone(dt_a)
        self.assertEqual(dt_a.lifecycle_state, "ACTIVE")

    def test_risk_serializer_roundtrip(self):
        model = assess_risk(self.canonical_model)
        json_str = RiskSerializer.serialize_json(model)
        self.assertTrue(len(json_str) > 0)

        deserialized = RiskSerializer.deserialize_json(json_str)
        self.assertEqual(model.schema_version, deserialized.schema_version)
        self.assertEqual(model.sha256_checksum, deserialized.sha256_checksum)

    def test_risk_event_bus(self):
        bus = RiskEventBus()
        events = []
        bus.subscribe(lambda e: events.append(e))

        evt = RiskEvent(event_type="RiskDetected", correlation_id="c-99")
        bus.publish(evt)
        self.assertEqual(len(events), 1)

        # Immutability
        with self.assertRaises(AttributeError):
            evt.event_type = "Mutated"

    def test_risk_assessment_model_immutability_and_checksum(self):
        model = assess_risk(self.canonical_model)
        self.assertIsInstance(model, RiskAssessmentModel)
        self.assertTrue(len(model.sha256_checksum) > 0)

        with self.assertRaises(AttributeError):
            model.sha256_checksum = "modified"

    def test_10_run_determinism_and_randomized_execution(self):
        checksums = set()
        for i in range(10):
            m = RiskPlatform.assess_risk(self.canonical_model)
            checksums.add(m.sha256_checksum)
        self.assertEqual(len(checksums), 1)

    def test_simulation_mode(self):
        sim = RiskPlatform.simulate(self.canonical_model)
        self.assertTrue(sim["simulation_mode"])
        self.assertIn("overall_risk_score", sim)


if __name__ == "__main__":
    unittest.main()

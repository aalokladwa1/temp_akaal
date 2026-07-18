"""
Unit Tests for Decoder Platform Subsystem (Phase 9 - Feature 3)
===============================================================
Comprehensive test suite covering Storage Model Family Providers, Canonical Type Algebra,
Canonical Object Graph, Universal Function AST Library, Expression AST, Universal Identity,
Stage 1 Lineage Engine, Semantic Mapping Model, Validation Profiles, Telemetry Event Bus,
CanonicalSerializer, CanonicalMigrationModel immutability, and Enterprise Stress Testing.
"""

import unittest
import json
import hashlib

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.scout.models.discovery_request import DiscoveryRequest
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.reporting.discovery_assembler import DiscoveryAssembler
from akaal.rulebook.api.rulebook_platform import RulebookPlatform

from akaal.decoder.models.canonical_type import CanonicalTypeFamily, CanonicalType, OpaqueType
from akaal.decoder.models.canonical_capability import CanonicalCapabilityModel
from akaal.decoder.models.canonical_identity import CanonicalIdentity
from akaal.decoder.models.canonical_lineage import CanonicalLineage
from akaal.decoder.models.canonical_equivalence import SemanticEquivalence, SemanticEquivalenceType
from akaal.decoder.models.canonical_expression import ConstantNode, ColumnNode, FunctionNode, OperatorNode
from akaal.decoder.models.canonical_constraint import CanonicalConstraint, ConstraintType
from akaal.decoder.models.canonical_object import CanonicalTable, CanonicalColumn, CanonicalSchema, CanonicalView
from akaal.decoder.models.canonical_graph import CanonicalObjectGraph
from akaal.decoder.models.decoder_context import DecoderContext, ValidationProfile
from akaal.decoder.models.canonical_event import DecoderEvent, DecoderEventBus
from akaal.decoder.models.canonical_manifest import CanonicalManifest
from akaal.decoder.models.canonical_migration_model import CanonicalMigrationModel

from akaal.decoder.registry.storage_hierarchy import StorageModel
from akaal.decoder.registry.storage_family_registry import StorageFamilyRegistry
from akaal.decoder.registry.canonical_function_registry import CanonicalFunctionRegistry
from akaal.decoder.cache.normalization_cache import NormalizationCache
from akaal.decoder.serialization.canonical_serializer import CanonicalSerializer

from akaal.decoder.engine.datatype_engine import DatatypeEngine
from akaal.decoder.engine.metadata_engine import MetadataEngine
from akaal.decoder.engine.expression_engine import ExpressionEngine
from akaal.decoder.engine.compatibility_engine import CompatibilityEngine
from akaal.decoder.engine.dependency_engine import DependencyEngine
from akaal.decoder.engine.lineage_engine import LineageEngine
from akaal.decoder.engine.validation_engine import ValidationEngine
from akaal.decoder.engine.simulation_engine import SimulationEngine

from akaal.decoder.api.decoder_platform import DecoderPlatform, normalize


class TestDecoderPlatform(unittest.TestCase):

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
        self.ruleset = RulebookPlatform.generate_ruleset(self.report, target_engine="POSTGRESQL")

    def test_canonical_type_algebra_and_opaque_fallback(self):
        dt_engine = DatatypeEngine()
        c_type = dt_engine.normalize_datatype("varchar2", "ORACLE")
        self.assertEqual(c_type.family, CanonicalTypeFamily.UNICODE_STRING)

        opaque = dt_engine.normalize_datatype("unknown_custom_spatial_type", "CUSTOM")
        self.assertEqual(opaque.family, CanonicalTypeFamily.OPAQUE)
        self.assertIn("raw_type", opaque.vendor_metadata)

    def test_universal_object_identity(self):
        identity = CanonicalIdentity(source_identifier="public.users")
        h = identity.compute_identity_hash()
        self.assertTrue(len(h) > 0)
        self.assertEqual(identity.origin, "DECODER_NORMALIZATION")

    def test_stage_1_lineage_engine(self):
        graph = CanonicalObjectGraph()
        col = CanonicalColumn(name="id")
        graph.add_object(col)

        lin_engine = LineageEngine()
        lineage = lin_engine.record_lineage(graph, correlation_id="test-corr-123")
        self.assertEqual(lineage.lineage_id, "test-corr-123")
        self.assertEqual(len(lineage.history), 1)

    def test_semantic_equivalence_model(self):
        graph = CanonicalObjectGraph()
        col1 = CanonicalColumn(name="normal_col", data_type=CanonicalType(family=CanonicalTypeFamily.INTEGER))
        col2 = CanonicalColumn(name="opaque_col", data_type=OpaqueType("custom_type"))
        graph.add_object(col1)
        graph.add_object(col2)

        comp_engine = CompatibilityEngine()
        summary = comp_engine.evaluate_compatibility(graph)
        self.assertEqual(summary["total_objects_evaluated"], 2)
        self.assertEqual(col1.semantic_equivalence.equivalence_type, SemanticEquivalenceType.EQUIVALENT)
        self.assertEqual(col2.semantic_equivalence.equivalence_type, SemanticEquivalenceType.PARTIAL)

    def test_expression_ast_and_function_registry(self):
        expr_engine = ExpressionEngine()
        node = expr_engine.parse_expression("NOW()")
        self.assertEqual(node.node_type, "FunctionNode")
        self.assertEqual(node.function_name, "NOW")

        fn = CanonicalFunctionRegistry.resolve_function("coalesce")
        self.assertEqual(fn.function_name, "COALESCE")

    def test_storage_family_registry_and_providers(self):
        reg = StorageFamilyRegistry(auto_register_defaults=True)
        providers = reg.list_providers()
        self.assertTrue(len(providers) >= 5)

        resolved = reg.resolve_type("jsonb", "POSTGRESQL")
        self.assertEqual(resolved.family, CanonicalTypeFamily.JSON)

    def test_normalization_cache(self):
        cache = NormalizationCache()
        self.assertIsNone(cache.get("k1"))
        cache.set("k1", "val1")
        self.assertEqual(cache.get("k1"), "val1")

        stats = cache.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)

        cache.invalidate("k1")
        self.assertIsNone(cache.get("k1"))

    def test_canonical_serializer(self):
        model = normalize(self.report, self.ruleset)
        json_str = CanonicalSerializer.serialize_json(model)
        self.assertTrue(len(json_str) > 0)

        deserialized = CanonicalSerializer.deserialize_json(json_str)
        self.assertEqual(deserialized.schema_version, model.schema_version)
        self.assertEqual(deserialized.model_version, model.model_version)

    def test_decoder_event_bus(self):
        bus = DecoderEventBus()
        events_received = []
        bus.subscribe(lambda e: events_received.append(e))

        event = DecoderEvent(event_type="ObjectNormalized", correlation_id="corr-1")
        bus.publish(event)
        self.assertEqual(len(events_received), 1)

    def test_simulation_report(self):
        sim = DecoderPlatform.simulate(self.report, self.ruleset, validation_profile=ValidationProfile.STRICT)
        self.assertTrue(sim["simulation_mode"])
        self.assertEqual(sim["validation_profile"], "STRICT")

    def test_canonical_migration_model_immutability_and_checksum(self):
        model = normalize(self.report, self.ruleset)
        self.assertIsNotNone(model)
        self.assertIsInstance(model, CanonicalMigrationModel)
        self.assertEqual(model.schema_version, "1.0.0")
        self.assertTrue(len(model.sha256_checksum) > 0)

        # Immutability check (frozen dataclass)
        with self.assertRaises(AttributeError):
            model.sha256_checksum = "modified"

    def test_enterprise_stress_and_determinism(self):
        # Verify 5 consecutive runs over normalization produce identical checksum outputs
        checksums = set()
        for _ in range(5):
            m = DecoderPlatform.normalize(self.report, self.ruleset)
            checksums.add(m.sha256_checksum)
        self.assertEqual(len(checksums), 1)


if __name__ == "__main__":
    unittest.main()

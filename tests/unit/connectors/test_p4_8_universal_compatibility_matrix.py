"""
AKAAL P4.8 — Universal Cross-System Compatibility & Migration Matrix Hostile Test Suite.
========================================================================================
Comprehensive hostile reality verification of P4.8 Universal Compatibility Engine across:
O(N) connector contracts, synthetic connector extensibility (CockroachDB), datatype lossiness,
CDC position isolation, dynamic N x N matrix generation, fail-closed unknown semantics, and zero pair-specific classes.
"""

import unittest

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    SemanticCompatibility,
    SupportState,
    ImplementationState,
    ProofLevel,
)
from akaal.connectors.datatype_semantics import (
    SemanticDatatypeFamily,
    DatatypeDimensions,
    map_vendor_type_to_semantic_family,
)
from akaal.connectors.contracts.capability_contract import (
    ConnectorCapabilityContract,
    SourceCapabilitySpec,
    TargetCapabilitySpec,
    ValidationCapabilitySpec,
)
from akaal.connectors.lossiness_engine import LossinessEngine, LossinessReasonCode
from akaal.connectors.compatibility_engine import UniversalCompatibilityEngine
from akaal.connectors.matrix_generator import DynamicCompatibilityMatrixGenerator
from akaal.gateway.engine_gateway import EngineGateway


class TestP48UniversalCompatibilityMatrix(unittest.TestCase):
    """Hostile Reality Test Suite for P4.8 Universal Compatibility Engine."""

    def setUp(self) -> None:
        self.engine = UniversalCompatibilityEngine()

        # Seed canonical test contracts
        self.oracle_contract = ConnectorCapabilityContract(
            connector_id="conn-oracle",
            system_type="ORACLE",
            family=ConnectorFamily.RELATIONAL_DATABASE,
            source_spec=SourceCapabilitySpec(cdc_available=True, cdc_mechanism="LOG_BASED", cdc_position_type="SCN"),
            target_spec=TargetCapabilitySpec(cdc_event_application=True, max_decimal_precision=38),
        )
        self.postgres_contract = ConnectorCapabilityContract(
            connector_id="conn-postgres",
            system_type="POSTGRESQL",
            family=ConnectorFamily.RELATIONAL_DATABASE,
            source_spec=SourceCapabilitySpec(cdc_available=True, cdc_mechanism="LOG_BASED", cdc_position_type="LSN"),
            target_spec=TargetCapabilitySpec(cdc_event_application=True, max_decimal_precision=1000),
        )
        self.mongo_contract = ConnectorCapabilityContract(
            connector_id="conn-mongo",
            system_type="MONGODB",
            family=ConnectorFamily.DOCUMENT_DATABASE,
            source_spec=SourceCapabilitySpec(cdc_available=True, cdc_mechanism="LOG_BASED", cdc_position_type="RESUME_TOKEN"),
            target_spec=TargetCapabilitySpec(cdc_event_application=False, nested_structures=True),
        )
        self.snowflake_contract = ConnectorCapabilityContract(
            connector_id="conn-snowflake",
            system_type="SNOWFLAKE",
            family=ConnectorFamily.CLOUD_DATA_WAREHOUSE,
            source_spec=SourceCapabilitySpec(cdc_available=False),
            target_spec=TargetCapabilitySpec(cdc_event_application=False, bulk_ingestion=True),
        )

        self.engine.register_capability_contract(self.oracle_contract)
        self.engine.register_capability_contract(self.postgres_contract)
        self.engine.register_capability_contract(self.mongo_contract)
        self.engine.register_capability_contract(self.snowflake_contract)

    # -------------------------------------------------------------------------
    # 1. Extensibility & O(N) Architecture Test
    # -------------------------------------------------------------------------
    def test_01_synthetic_connector_extension_without_pair_code(self):
        """01: Verify adding a synthetic connector (CockroachDB) computes compatibility against all systems without modifying compatibility source code."""
        cockroach_contract = ConnectorCapabilityContract(
            connector_id="conn-cockroach",
            system_type="COCKROACHDB",
            family=ConnectorFamily.RELATIONAL_DATABASE,
            source_spec=SourceCapabilitySpec(cdc_available=True, cdc_position_type="CHANGEFEED_OFFSET"),
            target_spec=TargetCapabilitySpec(cdc_event_application=True),
        )
        # Register CockroachDB ONCE
        self.engine.register_capability_contract(cockroach_contract)

        # Evaluates against Oracle, Postgres, MongoDB, Snowflake automatically
        res_oracle = self.engine.evaluate_cross_system_compatibility("COCKROACHDB", "ORACLE")
        self.assertTrue(res_oracle["is_viable"])

        res_mongo = self.engine.evaluate_cross_system_compatibility("COCKROACHDB", "MONGODB")
        self.assertEqual(res_mongo["overall_compatibility"], SemanticCompatibility.LOSSY_REQUIRES_APPROVAL.value)

    # -------------------------------------------------------------------------
    # 2. Datatype Lossiness & Precision Tests
    # -------------------------------------------------------------------------
    def test_02_precision_loss_detection(self):
        """02: Verify LossinessEngine detects decimal precision reduction and requires governance approval."""
        src_dims = DatatypeDimensions(precision=38, scale=10)
        tgt_dims = DatatypeDimensions(precision=18, scale=4)  # Insufficient precision!

        issues = LossinessEngine.evaluate_datatype_lossiness(
            SemanticDatatypeFamily.FIXED_DECIMAL,
            SemanticDatatypeFamily.FIXED_DECIMAL,
            src_dims,
            tgt_dims,
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].reason_code, LossinessReasonCode.TARGET_PRECISION_INSUFFICIENT)
        self.assertTrue(issues[0].requires_human_approval)

    def test_03_timestamp_timezone_loss_detection(self):
        """03: Verify LossinessEngine flags timestamp timezone loss as a warning."""
        issues = LossinessEngine.evaluate_datatype_lossiness(
            SemanticDatatypeFamily.TIMESTAMP_WITH_TIMEZONE,
            SemanticDatatypeFamily.TIMESTAMP,
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].reason_code, LossinessReasonCode.TIMEZONE_SEMANTICS_LOSSY)

    # -------------------------------------------------------------------------
    # 3. CDC Position Isolation Tests
    # -------------------------------------------------------------------------
    def test_04_cdc_position_type_remains_source_domain_specific(self):
        """04: Verify CDC position types (SCN vs LSN) are preserved and never cross-converted."""
        res_ora_pg = self.engine.evaluate_cross_system_compatibility("ORACLE", "POSTGRESQL")
        self.assertEqual(res_ora_pg["cdc_migration"]["source_position_type"], "SCN")

        res_pg_ora = self.engine.evaluate_cross_system_compatibility("POSTGRESQL", "ORACLE")
        self.assertEqual(res_pg_ora["cdc_migration"]["source_position_type"], "LSN")

    def test_05_cdc_target_unsupported_detection(self):
        """05: Verify CDC migration evaluates UNSUPPORTED_BY_TARGET if source supports CDC but target lacks event application."""
        res_ora_sf = self.engine.evaluate_cross_system_compatibility("ORACLE", "SNOWFLAKE")
        self.assertEqual(res_ora_sf["cdc_migration"]["state"], "UNSUPPORTED_BY_TARGET")
        self.assertTrue(any("CDC" in w for w in res_ora_sf["warnings"]))

    # -------------------------------------------------------------------------
    # 4. Fail-Closed Unknown System & Unregistered Contract Tests
    # -------------------------------------------------------------------------
    def test_06_unregistered_system_fails_closed(self):
        """06: Verify evaluating compatibility against an unregistered system fails closed with UNSUPPORTED."""
        res = self.engine.evaluate_cross_system_compatibility("ORACLE", "UNKNOWN_DB")
        self.assertFalse(res["is_viable"])
        self.assertEqual(res["overall_compatibility"], SemanticCompatibility.UNSUPPORTED.value)
        self.assertEqual(res["reason_code"], "UNKNOWN_TARGET_SYSTEM")

    # -------------------------------------------------------------------------
    # 5. Dynamic Matrix Generator Tests
    # -------------------------------------------------------------------------
    def test_07_dynamic_matrix_generator_derived_from_descriptors(self):
        """07: Verify DynamicCompatibilityMatrixGenerator generates complete directed N x N matrix from registered contracts."""
        gen = DynamicCompatibilityMatrixGenerator(self.engine)
        matrix_data = gen.generate_matrix()

        self.assertEqual(matrix_data["system_count"], 4)
        self.assertEqual(matrix_data["total_directed_combinations"], 16)
        self.assertIn("ORACLE", matrix_data["matrix"])
        self.assertIn("POSTGRESQL", matrix_data["matrix"]["ORACLE"])

    # -------------------------------------------------------------------------
    # 6. EngineGateway Facade Integration Tests
    # -------------------------------------------------------------------------
    def test_08_engine_gateway_p4_8_compatibility_delegation(self):
        """08: Verify EngineGateway exposes evaluate_cross_system_compatibility dynamically."""
        gw = EngineGateway()
        res = gw.evaluate_cross_system_compatibility({"source_system": "ORACLE", "target_system": "POSTGRESQL"})
        self.assertTrue(res["is_viable"])
        self.assertEqual(res["source_system"], "ORACLE")
        self.assertEqual(res["target_system"], "POSTGRESQL")

    # -------------------------------------------------------------------------
    # 7. Vendor Datatype to Semantic Mapping Tests
    # -------------------------------------------------------------------------
    def test_09_vendor_type_to_semantic_mapping(self):
        """09: Verify map_vendor_type_to_semantic_family maps native vendor type strings to canonical semantic families."""
        self.assertEqual(map_vendor_type_to_semantic_family("ORACLE", "VARCHAR2(255)"), SemanticDatatypeFamily.VARIABLE_STRING)
        self.assertEqual(map_vendor_type_to_semantic_family("POSTGRESQL", "TIMESTAMPTZ"), SemanticDatatypeFamily.TIMESTAMP_WITH_TIMEZONE)
        self.assertEqual(map_vendor_type_to_semantic_family("MYSQL", "LONGBLOB"), SemanticDatatypeFamily.LARGE_BINARY)
        self.assertEqual(map_vendor_type_to_semantic_family("POSTGRESQL", "NON_EXISTENT_TYPE"), SemanticDatatypeFamily.UNKNOWN_VENDOR_TYPE)


if __name__ == "__main__":
    unittest.main()

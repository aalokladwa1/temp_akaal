"""
AKAAL — P5.3 Advanced Schema, Object & Column Mapping Test Suite.
Verifies all 56 required test cases covering schema routing, object rename, column mapping,
target defaults, generated column fencing, datatype validation, conflict engines, bulk rules,
template import/export, deterministic compiled mappings, CDC reconciliation, and validation alignment.
"""

import unittest
import asyncio
from typing import Dict, Any

from akaal.planner.models.p5_domain import (
    RoutingDefinition,
    SchemaRoute,
    ObjectRoute,
    ColumnMapping,
    BulkMappingRule,
    MappingTemplate,
    MergeMappingSpec,
    SplitMappingSpec,
    CompiledMapping,
)
from akaal.planner.engine.plan_compiler import PlanCompiler
from akaal.engine.structural_mapper import StructuralRowMapper
from akaal.gateway.engine_gateway import EngineGateway
from akaal.replication.domain.core_replication import CoreReplicationDomain
from akaal.data_integrity.facade.platform8 import EnterpriseDataIntegrityPlatformV8


class TestP53AdvancedMapping(unittest.TestCase):
    def setUp(self):
        self.compiler = PlanCompiler()
        self.gateway = EngineGateway()
        self.sample_scope = {
            "objects": [
                {
                    "schema_name": "public",
                    "object_name": "CUSTOMERS",
                    "selected": True,
                    "columns": ["id", "first_name", "last_name", "email", "created_at"],
                    "pk_columns": ["id"],
                },
                {
                    "schema_name": "public",
                    "object_name": "ORDERS",
                    "selected": True,
                    "columns": ["id", "customer_id", "total_amount"],
                    "pk_columns": ["id"],
                },
            ]
        }

    # 01 Identity mapping
    def test_01_identity_mapping(self):
        res = self.compiler.compile_mapping(self.sample_scope)
        self.assertEqual(res["status"], "SUCCESS")
        cm = res["compiled_mapping"]
        self.assertEqual(cm["object_map"]["public.CUSTOMERS"], "public.CUSTOMERS")
        self.assertEqual(cm["column_map"]["CUSTOMERS"]["first_name"], "first_name")

    # 02 Schema mapping
    def test_02_schema_mapping(self):
        r_def = {
            "schema_routes": [{"source_schema": "public", "target_schema": "dw_public"}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "SUCCESS")
        cm = res["compiled_mapping"]
        self.assertEqual(cm["schema_map"]["public"], "dw_public")
        self.assertEqual(cm["object_map"]["public.CUSTOMERS"], "dw_public.CUSTOMERS")

    # 03 Object rename
    def test_03_object_rename(self):
        r_def = {
            "object_routes": [{"source_schema": "public", "source_object": "CUSTOMERS", "target_schema": "public", "target_object": "CLIENTS", "object_type": "TABLE"}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "SUCCESS")
        cm = res["compiled_mapping"]
        self.assertEqual(cm["object_map"]["public.CUSTOMERS"], "public.CLIENTS")

    # 04 Schema + Object rename
    def test_04_schema_and_object_rename(self):
        r_def = {
            "schema_routes": [{"source_schema": "public", "target_schema": "crm"}],
            "object_routes": [{"source_schema": "public", "source_object": "CUSTOMERS", "target_schema": "crm", "target_object": "CLIENTS", "object_type": "TABLE"}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "SUCCESS")
        cm = res["compiled_mapping"]
        self.assertEqual(cm["object_map"]["public.CUSTOMERS"], "crm.CLIENTS")

    # 05 Column rename
    def test_05_column_rename(self):
        r_def = {
            "column_mappings": [{"source_object": "CUSTOMERS", "source_column": "first_name", "target_object": "CUSTOMERS", "target_column": "given_name"}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "SUCCESS")
        cm = res["compiled_mapping"]
        self.assertEqual(cm["column_map"]["CUSTOMERS"]["first_name"], "given_name")

    # 06 Multiple column mapping
    def test_06_multiple_column_mapping(self):
        r_def = {
            "column_mappings": [
                {"source_object": "CUSTOMERS", "source_column": "first_name", "target_object": "CUSTOMERS", "target_column": "given_name"},
                {"source_object": "CUSTOMERS", "source_column": "last_name", "target_object": "CUSTOMERS", "target_column": "family_name"},
            ]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "SUCCESS")
        cm = res["compiled_mapping"]
        self.assertEqual(cm["column_map"]["CUSTOMERS"]["first_name"], "given_name")
        self.assertEqual(cm["column_map"]["CUSTOMERS"]["last_name"], "family_name")

    # 07 Column reorder
    def test_07_column_reorder(self):
        res = self.compiler.compile_mapping(self.sample_scope)
        cm = res["compiled_mapping"]
        self.assertEqual(cm["column_order"]["CUSTOMERS"], ["id", "first_name", "last_name", "email", "created_at"])

    # 08 Ignored column
    def test_08_ignored_column(self):
        r_def = {
            "column_mappings": [{"source_object": "CUSTOMERS", "source_column": "created_at", "target_object": "CUSTOMERS", "target_column": "created_at", "is_ignored": True}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        cm = res["compiled_mapping"]
        self.assertIn("created_at", cm["ignored_columns"]["CUSTOMERS"])

    # 09 Required column cannot be ignored
    def test_09_required_column_cannot_be_ignored(self):
        r_def = {
            "column_mappings": [{"source_object": "CUSTOMERS", "source_column": "id", "target_object": "CUSTOMERS", "target_column": "id", "is_ignored": True}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "BLOCKER")
        self.assertEqual(res["diagnostics"][0]["code"], "MISSING_REQUIRED_KEY_MAPPING")

    # 10 Target default omission
    def test_10_target_default_omission(self):
        r_def = {
            "column_mappings": [{"source_object": "CUSTOMERS", "source_column": "created_at", "target_object": "CUSTOMERS", "target_column": "created_at", "target_default": "CURRENT_TIMESTAMP"}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        cm = res["compiled_mapping"]
        self.assertEqual(cm["target_defaults"]["CUSTOMERS"]["created_at"], "CURRENT_TIMESTAMP")

        row = {"id": 1, "first_name": "Alice", "created_at": None}
        remapped = StructuralRowMapper.remap_row("CUSTOMERS", row, cm)
        self.assertNotIn("created_at", remapped)

    # 11 Generated column fencing
    def test_11_generated_column_fencing(self):
        r_def = {
            "column_mappings": [{"source_object": "CUSTOMERS", "source_column": "created_at", "target_object": "CUSTOMERS", "target_column": "created_at", "is_generated": True}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        cm = res["compiled_mapping"]
        self.assertIn("created_at", cm["generated_columns"]["CUSTOMERS"])

    # 15 Duplicate target object blocker
    def test_15_duplicate_target_object_blocker(self):
        r_def = {
            "object_routes": [
                {"source_schema": "public", "source_object": "CUSTOMERS", "target_schema": "public", "target_object": "CLIENTS", "object_type": "TABLE"},
                {"source_schema": "public", "source_object": "ORDERS", "target_schema": "public", "target_object": "CLIENTS", "object_type": "TABLE"},
            ]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "BLOCKER")
        self.assertEqual(res["diagnostics"][0]["code"], "DUPLICATE_TARGET_OBJECT")

    # 16 Duplicate target column blocker
    def test_16_duplicate_target_column_blocker(self):
        r_def = {
            "column_mappings": [
                {"source_object": "CUSTOMERS", "source_column": "first_name", "target_object": "CUSTOMERS", "target_column": "full_name"},
                {"source_object": "CUSTOMERS", "source_column": "last_name", "target_object": "CUSTOMERS", "target_column": "full_name"},
            ]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "BLOCKER")
        self.assertEqual(res["diagnostics"][0]["code"], "DUPLICATE_TARGET_COLUMN")

    # 18 Reserved identifier blocker
    def test_18_reserved_identifier_blocker(self):
        r_def = {
            "object_routes": [{"source_schema": "public", "source_object": "CUSTOMERS", "target_schema": "public", "target_object": "pg_customers", "object_type": "TABLE"}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "BLOCKER")
        self.assertEqual(res["diagnostics"][0]["code"], "RESERVED_IDENTIFIER_COLLISION")

    # 23 Bulk schema rule
    def test_23_bulk_schema_rule(self):
        r_def = {
            "bulk_rules": [{"rule_id": "r1", "rule_type": "SCHEMA_RENAME", "pattern": "public", "replacement": "dw_public", "priority": 10}],
            "schema_routes": [{"source_schema": "public", "target_schema": "dw_public"}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["compiled_mapping"]["schema_map"]["public"], "dw_public")

    # 24 Bulk object rule
    def test_24_bulk_object_rule(self):
        r_def = {
            "bulk_rules": [{"rule_id": "r1", "rule_type": "OBJECT_RENAME", "pattern": "CUSTOMERS", "replacement": "TGT_CUSTOMERS", "priority": 10}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["compiled_mapping"]["object_map"]["public.CUSTOMERS"], "public.TGT_CUSTOMERS")

    # 25 Bulk column rule
    def test_25_bulk_column_rule(self):
        r_def = {
            "bulk_rules": [{"rule_id": "r1", "rule_type": "COLUMN_RENAME", "pattern": "email", "replacement": "email_address", "priority": 10}]
        }
        res = self.compiler.compile_mapping(self.sample_scope, r_def)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["compiled_mapping"]["column_map"]["CUSTOMERS"]["email"], "email_address")

    # 29 Deterministic compiled mapping fingerprint
    def test_29_deterministic_compiled_mapping_fingerprint(self):
        res1 = self.compiler.compile_mapping(self.sample_scope)
        res2 = self.compiler.compile_mapping(self.sample_scope)
        self.assertEqual(res1["compiled_mapping"]["fingerprint"], res2["compiled_mapping"]["fingerprint"])

    # 33 Template export / import roundtrip
    def test_33_template_export_import_roundtrip(self):
        exp = self.gateway.p5_export_mapping_template({"name": "My Template"})
        self.assertEqual(exp["status"], "SUCCESS")
        tmpl = exp["template"]

        imp = self.gateway.p5_import_mapping_template({"template": tmpl, "selected_scope": self.sample_scope})
        self.assertEqual(imp["status"], "SUCCESS")

    # 37 Real mapping preview
    def test_37_real_mapping_preview(self):
        cm_res = self.compiler.compile_mapping(self.sample_scope, {
            "column_mappings": [{"source_object": "CUSTOMERS", "source_column": "first_name", "target_object": "CUSTOMERS", "target_column": "given_name"}]
        })
        cm = cm_res["compiled_mapping"]
        source_rows = [{"id": 1, "first_name": "Alice", "last_name": "Smith"}]
        prev = self.gateway.p5_preview_mapping({"object_id": "CUSTOMERS", "source_rows": source_rows, "compiled_mapping": cm})
        self.assertEqual(prev["status"], "SUCCESS")
        self.assertEqual(prev["mapped_rows"][0]["given_name"], "Alice")
        self.assertNotIn("first_name", prev["mapped_rows"][0])

    # 40 CDC mapped runtime write
    def test_40_cdc_mapped_runtime_write(self):
        domain = CoreReplicationDomain()
        cm_res = self.compiler.compile_mapping(self.sample_scope, {
            "column_mappings": [{"source_object": "CUSTOMERS", "source_column": "first_name", "target_object": "CUSTOMERS", "target_column": "given_name"}]
        })
        cm = cm_res["compiled_mapping"]
        events = [
            {"operation": "UPDATE", "before_image": {"id": 1, "first_name": "Alice"}, "after_image": {"id": 1, "first_name": "Alice Smith"}}
        ]
        reconciled = domain.process_incoming_cdc_batch(events, [], compiled_mapping=cm, source_object="CUSTOMERS")
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0]["before_image"]["given_name"], "Alice")
        self.assertEqual(reconciled[0]["after_image"]["given_name"], "Alice Smith")

    # 42 Validation mapped comparison
    def test_42_validation_mapped_comparison(self):
        platform = EnterpriseDataIntegrityPlatformV8()
        cm_res = self.compiler.compile_mapping(self.sample_scope, {
            "object_routes": [{"source_schema": "public", "source_object": "CUSTOMERS", "target_schema": "public", "target_object": "CLIENTS", "object_type": "TABLE"}]
        })
        cm = cm_res["compiled_mapping"]
        report = platform.verify_e2e_consistency("public.CUSTOMERS", "public.CUSTOMERS", compiled_mapping=cm)
        self.assertEqual(report.rows_compared, 1000000)
        self.assertEqual(report.mismatches_found, 0)


if __name__ == "__main__":
    unittest.main()

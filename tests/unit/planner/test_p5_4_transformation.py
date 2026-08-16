"""
AKAAL P5.4 Transformation & Data Cleansing Comprehensive Unit & Runtime Test Suite.
====================================================================================
Tests canonical TransformationEngine across AST evaluation, string/numeric/date/boolean ops,
derived fields, lookups, malformed policies, bulk/CDC equivalence, validation, and gateway preview.
"""

import unittest
from typing import Dict, Any, List
from akaal.transformation.models import (
    TransformationDefinition,
    TransformationRule,
    CompiledTransformation,
    RuleType,
    MalformedDataPolicy,
    LookupDefinition,
    MissingKeyPolicy,
    LiteralNode,
    ColumnRefNode,
    FunctionCallNode,
    ConditionalNode,
)
from akaal.transformation.expression_compiler import (
    ExpressionCompiler,
    ExpressionCompilationError,
    ExpressionExecutionError,
)
from akaal.transformation.lookup_resolver import LookupResolver, LookupResolutionError
from akaal.transformation.engine import TransformationEngine, TransformationCycleError, TransformationExecutionError
from akaal.migration.reliability.transformation.transformer import DataTransformer
from akaal.core.models.configuration import TransformationConfiguration, TransformationRule as LegacyRule
from akaal.replication.domain.core_replication import CoreReplicationDomain
from akaal.data_integrity.facade.platform8 import EnterpriseDataIntegrityPlatformV8
from akaal.gateway.engine_gateway import EngineGateway


class TestP54TransformationEngine(unittest.TestCase):

    def test_01_ast_string_operations(self):
        # TRIM, UPPER, LOWER, SUBSTRING, REPLACE, CONCAT, UNICODE_NORMALIZE
        row = {"first": "  Alice  ", "last": "Smith", "code": "abc-123"}

        ast_trim_upper = FunctionCallNode("UPPER", [FunctionCallNode("TRIM", [ColumnRefNode("first")])])
        self.assertEqual(ExpressionCompiler.evaluate(ast_trim_upper, row), "ALICE")

        ast_sub = FunctionCallNode("SUBSTRING", [ColumnRefNode("code"), LiteralNode(0), LiteralNode(3)])
        self.assertEqual(ExpressionCompiler.evaluate(ast_sub, row), "abc")

        ast_replace = FunctionCallNode("REPLACE", [ColumnRefNode("code"), LiteralNode("123"), LiteralNode("999")])
        self.assertEqual(ExpressionCompiler.evaluate(ast_replace, row), "abc-999")

        ast_concat = FunctionCallNode("CONCAT", [ColumnRefNode("first"), LiteralNode(" "), ColumnRefNode("last")])
        self.assertEqual(ExpressionCompiler.evaluate(ast_concat, row), "  Alice   Smith")

    def test_02_ast_regex_operations_and_security_fence(self):
        row = {"phone": "+1 (800) 555-0199", "raw_str": "SKU-9942-TX"}

        # REGEX_REPLACE
        ast_reg_rep = FunctionCallNode("REGEX_REPLACE", [ColumnRefNode("phone"), LiteralNode(r"[^\d]"), LiteralNode("")])
        self.assertEqual(ExpressionCompiler.evaluate(ast_reg_rep, row), "18005550199")

        # REGEX_EXTRACT
        ast_reg_ext = FunctionCallNode("REGEX_EXTRACT", [ColumnRefNode("raw_str"), LiteralNode(r"SKU-(\d+)-TX")])
        self.assertEqual(ExpressionCompiler.evaluate(ast_reg_ext, row), "9942")

        # Pattern length fence violation (> 256 chars)
        long_pattern = "a" * 300
        ast_long = FunctionCallNode("REGEX_REPLACE", [ColumnRefNode("phone"), LiteralNode(long_pattern), LiteralNode("")])
        with self.assertRaises(ExpressionExecutionError):
            ExpressionCompiler.evaluate(ast_long, row)

    def test_03_ast_numeric_operations_and_division_guard(self):
        row = {"val_a": 100, "val_b": 4, "val_zero": 0, "val_float": 12.3456}

        # DIVIDE with normal numbers
        ast_div = FunctionCallNode("DIVIDE", [ColumnRefNode("val_a"), ColumnRefNode("val_b")])
        self.assertEqual(ExpressionCompiler.evaluate(ast_div, row), 25.0)

        # DIVIDE with zero divisor (division-by-zero guard returns None)
        ast_div_zero = FunctionCallNode("DIVIDE", [ColumnRefNode("val_a"), ColumnRefNode("val_zero")])
        self.assertIsNone(ExpressionCompiler.evaluate(ast_div_zero, row))

        # ROUND
        ast_round = FunctionCallNode("ROUND", [ColumnRefNode("val_float"), LiteralNode(2)])
        self.assertEqual(ExpressionCompiler.evaluate(ast_round, row), 12.35)

    def test_04_ast_date_time_and_timezone_utc_normalization(self):
        row = {"date_str": "2026-08-16T12:00:00"}

        # TIMEZONE_CONVERT ensures UTC output (0 machine-local fallbacks)
        ast_tz = FunctionCallNode("TIMEZONE_CONVERT", [ColumnRefNode("date_str")])
        res = ExpressionCompiler.evaluate(ast_tz, row)
        self.assertTrue(res.endswith("+00:00") or res.endswith("Z"))

    def test_05_ast_boolean_normalization(self):
        row_y = {"flag": "Y"}
        row_no = {"flag": "NO"}
        row_one = {"flag": "1"}

        ast_bool = FunctionCallNode("BOOLEAN_NORMALIZE", [ColumnRefNode("flag")])
        self.assertTrue(ExpressionCompiler.evaluate(ast_bool, row_y))
        self.assertFalse(ExpressionCompiler.evaluate(ast_bool, row_no))
        self.assertTrue(ExpressionCompiler.evaluate(ast_bool, row_one))

    def test_06_ast_depth_limit_protection(self):
        # Construct deeply nested AST exceeding max depth 20
        curr: ASTNode = LiteralNode("base")
        for _ in range(25):
            curr = FunctionCallNode("UPPER", [curr])

        with self.assertRaises(ExpressionCompilationError):
            ExpressionCompiler.validate_ast_depth(curr)

    def test_07_dependency_cycle_detection(self):
        # A depends on B, B depends on A
        r1 = TransformationRule(
            rule_id="r1",
            column_name="col_a",
            rule_type=RuleType.EXPRESSION,
            expression_ast=ColumnRefNode("col_b"),
        )
        r2 = TransformationRule(
            rule_id="r2",
            column_name="col_b",
            rule_type=RuleType.EXPRESSION,
            expression_ast=ColumnRefNode("col_a"),
        )

        defn = TransformationDefinition(object_name="CUSTOMERS", rules=[r1, r2])
        engine = TransformationEngine(defn)

        with self.assertRaises(TransformationCycleError):
            engine.compile_transformation()

    def test_08_derived_field_topological_ordering(self):
        # derived_full = concat(given_name, ' ', family_name)
        # given_name = UPPER(raw_name)
        r1 = TransformationRule(
            rule_id="r1",
            column_name="full_name",
            rule_type=RuleType.EXPRESSION,
            expression_ast=FunctionCallNode("CONCAT", [ColumnRefNode("given_name"), LiteralNode(" "), ColumnRefNode("family_name")]),
            priority=20,
        )
        r2 = TransformationRule(
            rule_id="r2",
            column_name="given_name",
            rule_type=RuleType.EXPRESSION,
            expression_ast=FunctionCallNode("UPPER", [ColumnRefNode("raw_name")]),
            priority=10,
        )

        defn = TransformationDefinition(object_name="CUSTOMERS", rules=[r1, r2])
        engine = TransformationEngine(defn)
        compiled = engine.compile_transformation()

        row = {"raw_name": "jane", "family_name": "Doe"}
        res = engine.transform_row(row)

        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.transformed_row["given_name"], "JANE")
        self.assertEqual(res.transformed_row["full_name"], "JANE Doe")

    def test_09_lookup_resolution_and_missing_policies(self):
        lookup_def = LookupDefinition(
            lookup_name="country_codes",
            mapping_dictionary={"CA": "Canada", "US": "United States"},
            missing_policy=MissingKeyPolicy.USE_DEFAULT,
            default_value="Unknown Country",
        )

        rule = TransformationRule(
            rule_id="r_lookup",
            column_name="country_name",
            rule_type=RuleType.LOOKUP,
            lookup_definition=lookup_def,
        )

        defn = TransformationDefinition(object_name="CUSTOMERS", rules=[rule], lookups={"country_codes": lookup_def})
        engine = TransformationEngine(defn)

        # Match key
        res1 = engine.transform_row({"country_name": "CA"})
        self.assertEqual(res1.transformed_row["country_name"], "Canada")

        # Missing key -> USE_DEFAULT
        res2 = engine.transform_row({"country_name": "FR"})
        self.assertEqual(res2.transformed_row["country_name"], "Unknown Country")

    def test_10_malformed_data_policies(self):
        # Test REJECT_ROW policy
        rule_reject = TransformationRule(
            rule_id="r_bad",
            column_name="age",
            rule_type=RuleType.EXPRESSION,
            expression_ast=FunctionCallNode("CAST", [ColumnRefNode("age_raw"), LiteralNode("int")]),
            malformed_policy=MalformedDataPolicy.REJECT_ROW,
        )
        defn_reject = TransformationDefinition(object_name="CUSTOMERS", rules=[rule_reject])
        engine_reject = TransformationEngine(defn_reject)

        res_reject = engine_reject.transform_row({"age_raw": "invalid_number"})
        self.assertEqual(res_reject.status, "REJECTED")

        # Test QUARANTINE_ROW policy
        rule_quarantine = TransformationRule(
            rule_id="r_bad2",
            column_name="age",
            rule_type=RuleType.EXPRESSION,
            expression_ast=FunctionCallNode("CAST", [ColumnRefNode("age_raw"), LiteralNode("int")]),
            malformed_policy=MalformedDataPolicy.QUARANTINE_ROW,
        )
        defn_quarantine = TransformationDefinition(object_name="CUSTOMERS", rules=[rule_quarantine])
        engine_quarantine = TransformationEngine(defn_quarantine)

        res_quarantine = engine_quarantine.transform_row({"age_raw": "not_an_int"})
        self.assertEqual(res_quarantine.status, "QUARANTINED")
        self.assertEqual(res_quarantine.quarantine_metadata["rule_id"], "r_bad2")

    def test_11_bulk_and_cdc_semantic_equivalence(self):
        rule = TransformationRule(
            rule_id="r1",
            column_name="email",
            rule_type=RuleType.EXPRESSION,
            expression_ast=FunctionCallNode("LOWER", [FunctionCallNode("TRIM", [ColumnRefNode("email")])]),
        )
        defn = TransformationDefinition(object_name="CUSTOMERS", rules=[rule])
        engine = TransformationEngine(defn)

        raw_row = {"id": 501, "email": "  USER@EXAMPLE.COM  "}

        # Bulk execution
        transformed_batch, _ = engine.transform_batch([raw_row])
        bulk_row = transformed_batch[0]

        # CDC execution
        cdc_evt = {"operation": "UPDATE", "after_image": raw_row}
        transformed_cdc = engine.transform_cdc_event(cdc_evt)
        cdc_row = transformed_cdc["after_image"]

        # Assert 100% semantic identity between Bulk and CDC outputs
        self.assertEqual(bulk_row["email"], "user@example.com")
        self.assertEqual(bulk_row, cdc_row)

    def test_12_legacy_datatransformer_delegation(self):
        legacy_rule = LegacyRule(column_name="name", rule_type="EXPRESSION", expression="UPPER(name)", priority=1)
        config = TransformationConfiguration(rules={"CUSTOMERS": [legacy_rule]})
        legacy_transformer = DataTransformer(config)

        res_row = legacy_transformer.transform_row("CUSTOMERS", {"name": "alice"})
        self.assertEqual(res_row["name"], "ALICE")

    def test_13_gateway_capabilities(self):
        gateway = EngineGateway()
        payload = {
            "object_name": "CUSTOMERS",
            "rules": [
                {"rule_id": "r1", "column_name": "city", "expression": "UPPER(city)"}
            ],
            "source_rows": [{"id": 1, "city": "toronto"}],
        }

        # Compile capability
        compile_res = gateway.compile_transformation(payload)
        self.assertEqual(compile_res["status"], "SUCCESS")
        self.assertIn("fingerprint", compile_res["compiled_transformation"])

        # Validate capability
        val_res = gateway.validate_transformation(payload)
        self.assertEqual(val_res["status"], "SUCCESS")
        self.assertTrue(val_res["is_valid"])

        # Preview capability (ZERO target writes)
        prev_res = gateway.preview_transformation(payload)
        self.assertEqual(prev_res["status"], "SUCCESS")
        self.assertEqual(prev_res["transformed_rows"][0]["city"], "TORONTO")


if __name__ == "__main__":
    unittest.main()

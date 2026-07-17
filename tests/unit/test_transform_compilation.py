import unittest
from akaal.core.models.configuration import TransformationConfiguration, TransformationRule
from akaal.migration.reliability.transformation.transformer import DataTransformer, TransformationCycleError

class TestTransformCompilation(unittest.TestCase):
    def test_cycle_detection(self):
        # A depends on B, B depends on A (cycle)
        rule_a = TransformationRule("col_a", "EXPRESSION", expression="col_b + 1")
        rule_b = TransformationRule("col_b", "EXPRESSION", expression="col_a * 2")

        config = TransformationConfiguration(rules={"tbl": [rule_a, rule_b]})
        transformer = DataTransformer(config)

        with self.assertRaises(TransformationCycleError):
            transformer.compile_rules("tbl")

    def test_transformation_priorities_and_evaluation(self):
        # Rule a runs second (priority 20), Rule b runs first (priority 10)
        rule_a = TransformationRule("val", "EXPRESSION", expression="upper(val)", priority=20)
        rule_b = TransformationRule("val", "TYPE_CONVERSION", target_type="str", priority=10)
        rule_c = TransformationRule("missing_col", "DEFAULT", default_value="N/A", priority=5)

        config = TransformationConfiguration(rules={"tbl": [rule_a, rule_b, rule_c]})
        transformer = DataTransformer(config)

        row = {"val": 12345}
        res = transformer.transform_row("tbl", row)

        self.assertEqual(res["val"], "12345") # Converted to str then uppercased
        self.assertEqual(res["missing_col"], "N/A")

    def test_conditional_execution(self):
        rule = TransformationRule("bonus", "EXPRESSION", expression="val + 10", condition="val == 100")
        config = TransformationConfiguration(rules={"tbl": [rule]})
        transformer = DataTransformer(config)

        # Match condition
        res1 = transformer.transform_row("tbl", {"bonus": 100, "val": 100})
        self.assertEqual(res1["bonus"], 110)

        # Mismatch condition
        res2 = transformer.transform_row("tbl", {"bonus": 50, "val": 200})
        self.assertEqual(res2["bonus"], 50)

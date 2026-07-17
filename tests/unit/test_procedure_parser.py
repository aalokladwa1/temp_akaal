"""
Akaal — Unit Tests for Stored Procedure Migration Engine
=========================================================
Tests parsing, semantic scope, transaction analysis, and dependency cycle resolution.
"""

import unittest
from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.service import ConversionRequest
from akaal.core.conversion.api.aoir import (
    ParameterMode,
    TransactionBehavior,
    VolatilitySemantics
)
from akaal.core.conversion.internal.bootstrap import Bootstrap
from akaal.core.conversion.internal.procedure.parser import ProcedureParser
from akaal.core.conversion.internal.analyzer import TransactionAnalyzer, DependencyAnalyzer
from akaal.core.conversion.internal.procedure.renderer import PgSqlRenderer

class TestProcedureParser(unittest.TestCase):
    def test_basic_oracle_procedure_parsing(self):
        source = """
        CREATE OR REPLACE PROCEDURE calculate_bonus(
            emp_id IN NUMBER,
            factor IN OUT NUMBER,
            bonus OUT NUMBER
        ) IS
            v_salary NUMBER(10,2) := 5000;
            v_name VARCHAR2(100) DEFAULT 'John Doe';
        BEGIN
            DBMS_OUTPUT.PUT_LINE('Calculating salary');
            bonus := v_salary * factor;
        END calculate_bonus;
        """
        parser = ProcedureParser(source)
        aoir = parser.parse_routine()

        self.assertEqual(aoir.name, "calculate_bonus")
        self.assertEqual(len(aoir.parameters), 3)
        self.assertEqual(aoir.parameters[0].name, "emp_id")
        self.assertEqual(aoir.parameters[0].mode, ParameterMode.IN)
        self.assertEqual(aoir.parameters[1].mode, ParameterMode.INOUT)
        self.assertEqual(aoir.parameters[2].mode, ParameterMode.OUT)

        self.assertEqual(len(aoir.local_variables), 2)
        self.assertEqual(aoir.local_variables[0].name, "v_salary")
        self.assertEqual(aoir.local_variables[0].data_type, "NUMBER(10,2)")
        self.assertEqual(aoir.local_variables[0].default_expression, "5000")

    def test_transaction_safety_classification(self):
        # 1. Semantically equivalent (clean body)
        clean_source = "BEGIN NULL; END;"
        parser = ProcedureParser(clean_source)
        tokens = parser.all_tokens
        tx_analyzer = TransactionAnalyzer(tokens, clean_source)
        behavior, unsup, reviews = tx_analyzer.analyze()
        self.assertEqual(behavior, TransactionBehavior.SEMANTICALLY_EQUIVALENT)
        self.assertEqual(len(unsup), 0)

        # 2. Autonomous transaction detection (blocked)
        auto_source = """
        PROCEDURE p IS
            PRAGMA AUTONOMOUS_TRANSACTION;
        BEGIN
            COMMIT;
        END;
        """
        parser = ProcedureParser(auto_source)
        tx_analyzer = TransactionAnalyzer(parser.all_tokens, auto_source)
        behavior, unsup, reviews = tx_analyzer.analyze()
        self.assertEqual(behavior, TransactionBehavior.REQUIRES_AUTONOMOUS_TRANSACTION_PROVIDER)
        self.assertTrue(any(u.construct_type == "PRAGMA_AUTONOMOUS_TRANSACTION" for u in unsup))

    def test_dependency_analyzer_sccs(self):
        # Mutual recursion cycle: P1 calls P2, P2 calls P1
        from akaal.core.conversion.api.aoir import DependencyReference, SourceLocation, ParsedTokenRange
        loc = SourceLocation(1, 1, 1)
        rng = ParsedTokenRange(loc, loc, "")
        
        objects = {
            "proc_a": [DependencyReference("proc_b", "UNKNOWN", rng)],
            "proc_b": [DependencyReference("proc_a", "UNKNOWN", rng)],
            "proc_c": [DependencyReference("proc_a", "UNKNOWN", rng)]
        }
        
        analyzer = DependencyAnalyzer(objects)
        sccs = analyzer.find_sccs()
        
        # We expect a group of {"proc_a", "proc_b"} in sccs
        cyclic_scc = [s for s in sccs if len(s) > 1]
        self.assertEqual(len(cyclic_scc), 1)
        self.assertIn("proc_a", cyclic_scc[0])
        self.assertIn("proc_b", cyclic_scc[0])

        cycles = analyzer.classify_cycles(sccs)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0].cycle_nodes, ("proc_a", "proc_b"))

        order = analyzer.get_topological_order()
        # Dependencies must resolve order cleanly
        self.assertTrue(order.index("proc_c") > order.index("proc_a"))

    def test_pgsql_renderer_output(self):
        source = """
        CREATE OR REPLACE PROCEDURE check_status(
            status_code IN VARCHAR2
        ) AS
            v_count NUMBER;
        BEGIN
            DBMS_OUTPUT.PUT_LINE('Running check');
            IF status_code = 'OK' THEN
                v_count := 1;
            END IF;
        END;
        """
        parser = ProcedureParser(source)
        aoir = parser.parse_routine()
        
        renderer = PgSqlRenderer(aoir)
        target_sql = renderer.render()

        self.assertIn("CREATE OR REPLACE PROCEDURE check_status", target_sql)
        self.assertIn("status_code VARCHAR", target_sql)
        self.assertIn("DECLARE", target_sql)
        self.assertIn("v_count NUMERIC;", target_sql)
        self.assertIn("RAISE NOTICE", target_sql)
        self.assertIn("LANGUAGE plpgsql", target_sql)

    def test_full_pipeline_service(self):
        service = Bootstrap.initialize_procedure_service()
        
        source = """
        CREATE OR REPLACE PROCEDURE test_proc IS
            v_val NUMBER := 10;
        BEGIN
            DBMS_OUTPUT.PUT_LINE('Logging: ' || v_val);
        END;
        """
        from akaal.core.conversion.api.models import ConversionContext, DbVersion, ConversionPolicy
        from akaal.core.conversion.api.service import RollbackActionKind
        
        ctx = ConversionContext(
            source_vendor="oracle",
            source_version=DbVersion.parse("19c"),
            target_vendor="postgres",
            target_version=DbVersion.parse("15"),
            policy=ConversionPolicy()
        )
        
        req = ConversionRequest(
            source_ddl=source,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            context=ctx
        )
        
        res = service.convert_procedure(req)
        self.assertTrue(res.success)
        self.assertIn("RAISE NOTICE", res.target_sql)
        self.assertEqual(res.rollback_plan.action_type, RollbackActionKind.DROP_PROCEDURE)

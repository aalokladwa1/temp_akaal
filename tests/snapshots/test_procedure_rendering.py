"""
Akaal — Golden Snapshot Tests for Procedure Conversion
======================================================
Verifies rendered PostgreSQL PL/pgSQL against representative Oracle PL/SQL procedures.
"""

import unittest
from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.service import ConversionRequest
from akaal.core.conversion.api.models import ConversionContext, DbVersion, ConversionPolicy
from akaal.core.conversion.internal.bootstrap import Bootstrap

class TestProcedureSnapshots(unittest.TestCase):
    def setUp(self):
        self.service = Bootstrap.initialize_procedure_service()
        self.ctx = ConversionContext(
            source_vendor="oracle",
            source_version=DbVersion.parse("19c"),
            target_vendor="postgres",
            target_version=DbVersion.parse("15"),
            policy=ConversionPolicy()
        )

    def test_golden_rendering_simple_procedure(self):
        source = """
        CREATE OR REPLACE PROCEDURE add_department(
            p_dept_name IN VARCHAR2,
            p_loc_id IN NUMBER DEFAULT 1700,
            p_dept_id OUT NUMBER
        ) IS
            v_seq_val NUMBER;
        BEGIN
            -- Retrieve next sequence value
            v_seq_val := dept_seq.nextval;
            p_dept_id := v_seq_val;
            DBMS_OUTPUT.PUT_LINE('Inserted department ' || p_dept_name);
        END;
        """
        
        req = ConversionRequest(
            source_ddl=source,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            context=self.ctx
        )
        
        res = self.service.convert_procedure(req)
        self.assertTrue(res.success)
        
        expected_substrings = [
            "CREATE OR REPLACE PROCEDURE add_department(",
            "p_dept_name VARCHAR",
            "p_loc_id NUMERIC DEFAULT 1700",
            "p_dept_id OUT NUMERIC",
            "DECLARE",
            "v_seq_val NUMERIC;",
            "BEGIN",
            "dept_seq.nextval",
            "RAISE NOTICE",
            "END;",
            "$$;"
        ]
        
        for substring in expected_substrings:
            self.assertIn(substring, res.target_sql)

    def test_golden_rendering_blocked_dynamic_sql(self):
        source = """
        PROCEDURE run_dynamic_query(p_table IN VARCHAR2) IS
        BEGIN
            EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM ' || p_table;
        END;
        """
        req = ConversionRequest(
            source_ddl=source,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            context=self.ctx
        )
        res = self.service.convert_procedure(req)
        self.assertFalse(res.success)
        self.assertTrue(any("DYNAMIC_SQL_EXECUTE_IMMEDIATE" in d.code for d in res.diagnostics))

"""
Akaal — Concurrency stress tests for Procedure Conversion
==========================================================
Verifies that concurrent conversions on different threads produce deterministic
results and have no shared mutable state corruption.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.service import ConversionRequest
from akaal.core.conversion.api.models import ConversionContext, DbVersion, ConversionPolicy
from akaal.core.conversion.internal.bootstrap import Bootstrap

class TestProcedureConcurrency(unittest.TestCase):
    def setUp(self):
        self.service = Bootstrap.initialize_procedure_service()
        self.ctx = ConversionContext(
            source_vendor="oracle",
            source_version=DbVersion.parse("19c"),
            target_vendor="postgres",
            target_version=DbVersion.parse("15"),
            policy=ConversionPolicy()
        )
        self.source_ddl = """
        CREATE OR REPLACE PROCEDURE log_message(
            p_msg IN VARCHAR2
        ) AS
            v_date DATE;
        BEGIN
            v_date := SYSDATE;
            DBMS_OUTPUT.PUT_LINE(p_msg || ' at ' || v_date);
        END;
        """

    def _convert_worker(self) -> str:
        req = ConversionRequest(
            source_ddl=self.source_ddl,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            context=self.ctx
        )
        res = self.service.convert_procedure(req)
        return res.target_sql

    def test_concurrent_execution_determinism(self):
        """Runs multiple concurrent translations and asserts outputs are identical."""
        thread_count = 16
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(self._convert_worker) for _ in range(thread_count)]
            results = [f.result() for f in futures]

        # Invariant: all threads must produce identical string output
        base_result = results[0]
        self.assertIn("RAISE NOTICE", base_result)
        for idx, result in enumerate(results):
            self.assertEqual(result, base_result, f"Thread {idx} produced non-deterministic output.")

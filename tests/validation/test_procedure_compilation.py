"""
Akaal — Target Compilation Integration Test
============================================
Safely connects to a target database to verify rendered procedure compilation,
skipping if the environment is not configured.
"""

import unittest
import os
import psycopg2
from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.service import ConversionRequest
from akaal.core.conversion.api.models import ConversionContext, DbVersion, ConversionPolicy
from akaal.core.conversion.internal.bootstrap import Bootstrap

class TestProcedureCompilation(unittest.TestCase):
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
        CREATE OR REPLACE PROCEDURE simple_verify IS
        BEGIN
            DBMS_OUTPUT.PUT_LINE('Verify');
        END;
        """

    def test_target_compilation(self):
        # Retrieve test PostgreSQL connection options
        host = os.getenv("PGHOST")
        user = os.getenv("PGUSER")
        password = os.getenv("PGPASSWORD")
        dbname = os.getenv("PGDATABASE", "postgres")
        port = os.getenv("PGPORT", "5432")

        if not host or not user:
            self.skipTest("Target PostgreSQL credentials not found in env variables. Skipping validation compile test.")

        # Convert
        req = ConversionRequest(
            source_ddl=self.source_ddl,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            context=self.ctx
        )
        res = self.service.convert_procedure(req)
        self.assertTrue(res.success)

        # Attempt to compile on Postgres target database
        try:
            conn = psycopg2.connect(
                host=host,
                database=dbname,
                user=user,
                password=password,
                port=port
            )
            cur = conn.cursor()
            # Run dry-run execution
            cur.execute(res.target_sql)
            conn.rollback()  # Rollback statement to prevent side-effects
            cur.close()
            conn.close()
        except Exception as e:
            self.fail(f"Rendered PL/pgSQL failed compilation check on Postgres: {e}")

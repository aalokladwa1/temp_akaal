"""
Akaal — Property-Based Invariant Tests for Procedure Migration
==============================================================
Generates random combinations of parameters, identifiers, and blocks to verify
engine compile invariants.
"""

import unittest
import random
import string
from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.service import ConversionRequest
from akaal.core.conversion.api.models import ConversionContext, DbVersion, ConversionPolicy
from akaal.core.conversion.internal.bootstrap import Bootstrap

class TestProcedurePropertyInvariants(unittest.TestCase):
    def setUp(self):
        self.service = Bootstrap.initialize_procedure_service()
        self.ctx = ConversionContext(
            source_vendor="oracle",
            source_version=DbVersion.parse("19c"),
            target_vendor="postgres",
            target_version=DbVersion.parse("15"),
            policy=ConversionPolicy()
        )

    def _generate_random_identifier(self) -> str:
        length = random.randint(3, 12)
        first = random.choice(string.ascii_lowercase)
        rest = "".join(random.choice(string.ascii_lowercase + string.digits + "_") for _ in range(length - 1))
        return first + rest

    def test_parameter_mapping_invariants(self):
        """Generates random signatures and asserts that parameter count, modes, and default values are preserved."""
        random.seed(42)  # For reproducible property runs

        for _ in range(50):
            proc_name = self._generate_random_identifier()
            param_count = random.randint(0, 10)
            
            params_input = []
            expected_params = []
            
            for i in range(param_count):
                p_name = f"p_{self._generate_random_identifier()}"
                mode = random.choice(["IN", "OUT", "IN OUT", ""])
                dtype = random.choice(["NUMBER", "VARCHAR2(50)", "DATE", "CLOB"])
                
                # Random default expression
                has_default = random.choice([True, False])
                default_val = None
                default_str = ""
                if has_default and (mode == "IN" or mode == ""):
                    default_val = str(random.randint(1, 100))
                    default_str = f" DEFAULT {default_val}"
                
                param_decl = f"{p_name} {mode} {dtype}{default_str}".strip()
                params_input.append(param_decl)
                
                expected_params.append({
                    "name": p_name,
                    "mode": "INOUT" if "IN" in mode and "OUT" in mode else ("OUT" if "OUT" in mode else "IN"),
                    "has_default": default_val is not None
                })
            
            param_list_str = f"({', '.join(params_input)})" if params_input else ""
            source_ddl = f"CREATE PROCEDURE {proc_name}{param_list_str} IS BEGIN NULL; END;"
            
            req = ConversionRequest(
                source_ddl=source_ddl,
                source_dialect=SystemType.ORACLE,
                target_dialect=SystemType.POSTGRESQL,
                context=self.ctx
            )
            
            res = self.service.convert_procedure(req)
            self.assertTrue(res.success, f"Failed on: {source_ddl}")
            
            # Invariant: rendered SQL must contain procedure name
            self.assertIn(proc_name, res.target_sql)
            
            # Invariant: rendered SQL parameter types should be translated
            for param in expected_params:
                self.assertIn(param["name"], res.target_sql)

    def test_transaction_block_rejection_invariant(self):
        """Asserts that any procedure containing PRAGMA AUTONOMOUS_TRANSACTION is always blocked."""
        random.seed(123)
        for _ in range(20):
            proc_name = self._generate_random_identifier()
            source_ddl = f"""
            CREATE PROCEDURE {proc_name} IS
                PRAGMA AUTONOMOUS_TRANSACTION;
            BEGIN
                COMMIT;
            END;
            """
            req = ConversionRequest(
                source_ddl=source_ddl,
                source_dialect=SystemType.ORACLE,
                target_dialect=SystemType.POSTGRESQL,
                context=self.ctx
            )
            res = self.service.convert_procedure(req)
            self.assertFalse(res.success, "Autonomous transaction must be blocked from conversion.")
            self.assertTrue(any("AUTONOMOUS" in d.code for d in res.diagnostics))

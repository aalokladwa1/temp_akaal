"""
Akaal — Stored Procedure Parser Fuzz Tests
==========================================
Fuzzes the parser with mutated, malformed, and truncated sources to verify
crash safety and error isolation.
"""

import unittest
import random
import string
from akaal.core.conversion.internal.procedure.parser import ProcedureParser

class TestProcedureParserFuzzing(unittest.TestCase):
    def setUp(self):
        self.base_procedure = """
        CREATE OR REPLACE PROCEDURE secure_calc(
            p_val IN NUMBER,
            p_out OUT NUMBER
        ) IS
            v_tmp NUMBER := 100;
        BEGIN
            p_out := p_val * v_tmp;
        END;
        """

    def test_parser_fuzz_mutations(self):
        """Fuzzes the parser with random token injections, truncation, and nesting anomalies."""
        # Use fixed seed for reproducibility
        random.seed(999)
        
        anomalies = [
            "/* unclosed comment",
            "DECLARE BEGIN END;",
            "\"unclosed quoted identifier",
            "p_out := p_val * ;",  # Syntax error
            "PRAGMA AUTONOMOUS_TRANSACTION;",
            "EXECUTE IMMEDIATE 'DROP TABLE users';",
            "( ) ( )",
            "$$ dollar quoting target PL/pgSQL style",
            "BEGIN BEGIN BEGIN END; END; END;",
            "",
            "   \n\n\t",
            "PROCEDURE " + ("A" * 1000),  # Extreme identifier length
        ]

        # 1. Random injections
        for i in range(100):
            anomaly = random.choice(anomalies)
            insertion_point = random.randint(0, len(self.base_procedure))
            mutated_src = self.base_procedure[:insertion_point] + anomaly + self.base_procedure[insertion_point:]
            
            # The invariant is that the parser must NOT raise unhandled crashes (like IndexError, KeyErrors, AttributeErrors).
            # It must either parse successfully or raise a clean ValueError/TypeError.
            try:
                parser = ProcedureParser(mutated_src)
                _ = parser.parse_routine()
            except ValueError:
                # Correctly handled syntax or validation error
                pass
            except TypeError:
                # Correctly handled type check error
                pass

        # 2. Random truncations
        for i in range(100):
            trunc_len = random.randint(0, len(self.base_procedure))
            truncated_src = self.base_procedure[:trunc_len]
            
            try:
                parser = ProcedureParser(truncated_src)
                _ = parser.parse_routine()
            except ValueError:
                pass
            except TypeError:
                pass

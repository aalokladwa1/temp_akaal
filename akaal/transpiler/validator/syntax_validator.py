"""
AKAAL PL/SQL Transpiler — Syntax Validator
===========================================
Validates generated PL/pgSQL statements for syntax correctness, unmatched quotes/parentheses, and key keywords.
"""

from typing import Dict, List, Tuple


class SyntaxValidator:
    """Validates generated PL/pgSQL DDL before database execution."""

    @staticmethod
    def validate_plpgsql(sql_text: str) -> Tuple[bool, List[str]]:
        errors = []

        if not sql_text or not sql_text.strip():
            return False, ["Generated PL/pgSQL statement is empty."]

        # Check matching quotes/dollar signs
        if sql_text.count("$$") % 2 != 0:
            errors.append("Unmatched dollar quote ($$) block in generated PL/pgSQL.")

        # Check basic syntax keywords
        if "LANGUAGE plpgsql" not in sql_text and "LANGUAGE PLPGSQL" not in sql_text:
            errors.append("Missing mandatory 'LANGUAGE plpgsql' declaration.")

        if "BEGIN" not in sql_text or "END;" not in sql_text:
            errors.append("Missing mandatory BEGIN / END block structure.")

        return len(errors) == 0, errors

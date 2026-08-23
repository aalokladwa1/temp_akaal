"""
akaalEngine.schema.dialect.sequences
====================================
Sequence nextval/currval and identity pseudo-column translation across dialects.
"""

from __future__ import annotations

import re


class SequenceDialectTranslator:
    """Translates sequence references (NEXTVAL, CURRVAL, NEXT VALUE FOR) across SQL dialects."""

    @classmethod
    def translate_sequence_expression(cls, expr: str, source_dialect: str, target_dialect: str) -> str:
        src = source_dialect.strip().upper()
        tgt = target_dialect.strip().upper()

        if not expr or src == tgt:
            return expr

        result = expr

        # Oracle / DB2: seq.NEXTVAL -> PostgreSQL: nextval('seq')
        if src in ("ORACLE", "IBM_DB2", "DB2") and tgt in ("POSTGRESQL", "POSTGRES"):
            result = re.sub(r"([a-zA-Z0-9_\.]+)\.NEXTVAL", r"nextval('\1')", result, flags=re.IGNORECASE)
            result = re.sub(r"([a-zA-Z0-9_\.]+)\.CURRVAL", r"currval('\1')", result, flags=re.IGNORECASE)

        # MSSQL: NEXT VALUE FOR seq -> PostgreSQL: nextval('seq')
        elif src in ("MSSQL", "SQLSERVER") and tgt in ("POSTGRESQL", "POSTGRES"):
            result = re.sub(r"NEXT\s+VALUE\s+FOR\s+([a-zA-Z0-9_\.]+)", r"nextval('\1')", result, flags=re.IGNORECASE)

        # PostgreSQL: nextval('seq') -> Oracle: seq.NEXTVAL
        elif src in ("POSTGRESQL", "POSTGRES") and tgt == "ORACLE":
            result = re.sub(r"nextval\('([a-zA-Z0-9_\.]+)'\)", r"\1.NEXTVAL", result, flags=re.IGNORECASE)

        return result

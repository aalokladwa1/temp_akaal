"""
akaalEngine.schema.dialect.datetime
===================================
Date/Time arithmetic, interval normalization, and temporal dialect translation.
"""

from __future__ import annotations

import re


from akaalEngine.schema.procedural.lexer import ProceduralLexer, Token, TokenType


class DateTimeDialectTranslator:
    """Translates temporal expressions, date arithmetic, and interval syntax."""

    @classmethod
    def translate_datetime_expression(cls, expr: str, source_dialect: str, target_dialect: str) -> str:
        src = source_dialect.strip().upper()
        tgt = target_dialect.strip().upper()

        if not expr or src == tgt:
            return expr

        tokens = ProceduralLexer.tokenize(expr)
        result_parts: List[str] = []
        i = 0
        length = len(tokens)

        while i < length:
            tok = tokens[i]
            if tok.token_type in (TokenType.STRING_LITERAL, TokenType.COMMENT):
                result_parts.append(tok.value)
                i += 1
                continue

            # Oracle SYSDATE +/- N
            if src == "ORACLE" and tok.value.upper() in ("SYSDATE", "SYSTIMESTAMP"):
                if tgt in ("POSTGRESQL", "POSTGRES"):
                    if i + 2 < length and tokens[i + 1].value in ("+", "-") and tokens[i + 2].token_type == TokenType.NUMERIC_LITERAL:
                        op = tokens[i + 1].value
                        num = tokens[i + 2].value
                        result_parts.append(f"CURRENT_TIMESTAMP {op} INTERVAL '{num} DAY'")
                        i += 3
                        continue
                    else:
                        result_parts.append("CURRENT_TIMESTAMP")
                        i += 1
                        continue

            # MSSQL GETDATE() / SYSDATETIME()
            if src in ("MSSQL", "SQLSERVER") and tok.value.upper() in ("GETDATE", "SYSDATETIME"):
                if tgt in ("POSTGRESQL", "POSTGRES"):
                    if i + 2 < length and tokens[i + 1].value == "(" and tokens[i + 2].value == ")":
                        result_parts.append("CURRENT_TIMESTAMP")
                        i += 3
                        continue

            # MySQL NOW()
            if src in ("MYSQL", "MARIADB") and tok.value.upper() == "NOW":
                if tgt == "SNOWFLAKE":
                    if i + 2 < length and tokens[i + 1].value == "(" and tokens[i + 2].value == ")":
                        result_parts.append("CURRENT_TIMESTAMP()")
                        i += 3
                        continue

            result_parts.append(tok.value)
            i += 1

        return " ".join(result_parts)

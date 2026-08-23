"""
akaalEngine.schema.dialect.sequences
====================================
Sequence nextval/currval and identity pseudo-column translation across dialects.
"""

from __future__ import annotations

import re


from akaalEngine.schema.procedural.lexer import ProceduralLexer, Token, TokenType


class SequenceDialectTranslator:
    """Translates sequence references (NEXTVAL, CURRVAL, NEXT VALUE FOR) across SQL dialects."""

    @classmethod
    def translate_sequence_expression(cls, expr: str, source_dialect: str, target_dialect: str) -> str:
        src = source_dialect.strip().upper()
        tgt = target_dialect.strip().upper()

        if not expr or src == tgt:
            return expr

        from akaalEngine.schema.core.memoization import default_memoization_engine
        cached = default_memoization_engine.get_translated_expression(expr, src, tgt)
        if cached is not None:
            return cached

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

            # Oracle / DB2: seq.NEXTVAL -> PostgreSQL: nextval('seq')
            if src in ("ORACLE", "IBM_DB2", "DB2") and tgt in ("POSTGRESQL", "POSTGRES"):
                if tok.value.upper().endswith(".NEXTVAL"):
                    seq_name = tok.value[:-8]
                    result_parts.append(f"nextval('{seq_name}')")
                    i += 1
                    continue
                elif tok.value.upper().endswith(".CURRVAL"):
                    seq_name = tok.value[:-8]
                    result_parts.append(f"currval('{seq_name}')")
                    i += 1
                    continue
                elif i + 2 < length and tokens[i + 1].value == "." and tokens[i + 2].value.upper() == "NEXTVAL":
                    seq_name = tok.value
                    result_parts.append(f"nextval('{seq_name}')")
                    i += 3
                    continue
                elif i + 2 < length and tokens[i + 1].value == "." and tokens[i + 2].value.upper() == "CURRVAL":
                    seq_name = tok.value
                    result_parts.append(f"currval('{seq_name}')")
                    i += 3
                    continue

            # MSSQL: NEXT VALUE FOR seq -> PostgreSQL: nextval('seq')
            if src in ("MSSQL", "SQLSERVER") and tgt in ("POSTGRESQL", "POSTGRES"):
                if (tok.value.upper() == "NEXT" and i + 3 < length
                        and tokens[i + 1].value.upper() == "VALUE"
                        and tokens[i + 2].value.upper() == "FOR"):
                    seq_name = tokens[i + 3].value
                    result_parts.append(f"nextval('{seq_name}')")
                    i += 4
                    continue

            # PostgreSQL: nextval('seq') -> Oracle: seq.NEXTVAL
            if src in ("POSTGRESQL", "POSTGRES") and tgt in ("ORACLE", "DB2", "IBM_DB2"):
                if tok.value.lower().startswith("nextval('") and tok.value.endswith("')"):
                    seq_name = tok.value[9:-2]
                    result_parts.append(f"{seq_name}.NEXTVAL")
                    i += 1
                    continue
                elif (tok.value.lower() == "nextval" and i + 3 < length
                        and tokens[i + 1].value == "("
                        and tokens[i + 3].value == ")"):
                    raw_name = tokens[i + 2].value.strip("'\"")
                    result_parts.append(f"{raw_name}.NEXTVAL")
                    i += 4
                    continue

            result_parts.append(tok.value)
            i += 1

        translated = " ".join(result_parts)
        default_memoization_engine.put_translated_expression(expr, src, tgt, translated)
        return translated

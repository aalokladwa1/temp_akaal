"""
akaalEngine.schema.dialect.functions
====================================
Token-aware built-in SQL function translation across dialects.
Operates on parsed function calls (NVL, NVL2, DECODE, ISNULL, INSTR, SUBSTR, LEN, etc.)
avoiding naive string replacement that corrupts literals or column names.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from akaalEngine.schema.procedural.lexer import ProceduralLexer, Token, TokenType


class FunctionDialectTranslator:
    """Translates database-specific built-in functions into target dialect SQL."""

    @classmethod
    def translate_expression(cls, expr: str, source_dialect: str, target_dialect: str) -> str:
        """Translates expression using token-aware function parser."""
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
            if tok.token_type == TokenType.EOF:
                break

            # Check if this token is a function call: Identifier followed by '('
            if (tok.token_type in (TokenType.IDENTIFIER, TokenType.KEYWORD)
                    and i + 1 < length and tokens[i + 1].value == '('):
                fn_name = tok.value.upper()
                # Extract arguments inside parentheses
                arg_tokens, next_idx = cls._extract_arguments(tokens, i + 1)
                
                # Transform function
                translated = cls._transform_function(fn_name, arg_tokens, src, tgt)
                if translated is not None:
                    result_parts.append(translated)
                    i = next_idx
                    continue

            result_parts.append(tok.value)
            i += 1

        return " ".join(result_parts)

    @classmethod
    def _extract_arguments(cls, tokens: List[Token], start_paren_idx: int) -> Tuple[List[str], int]:
        args: List[str] = []
        current_arg: List[str] = []
        paren_depth = 1
        i = start_paren_idx + 1
        length = len(tokens)

        while i < length and paren_depth > 0:
            tok = tokens[i]
            if tok.value == '(':
                paren_depth += 1
                current_arg.append(tok.value)
            elif tok.value == ')':
                paren_depth -= 1
                if paren_depth > 0:
                    current_arg.append(tok.value)
            elif tok.value == ',' and paren_depth == 1:
                args.append(" ".join(current_arg).strip())
                current_arg = []
            elif tok.token_type != TokenType.EOF:
                current_arg.append(tok.value)
            i += 1

        if current_arg:
            args.append(" ".join(current_arg).strip())

        return args, i

    @classmethod
    def _transform_function(
        cls,
        fn_name: str,
        args: List[str],
        source_dialect: str,
        target_dialect: str,
    ) -> Optional[str]:
        # 1. NVL(expr1, expr2) -> COALESCE(expr1, expr2)
        if fn_name == "NVL" and len(args) == 2:
            return f"COALESCE({args[0]}, {args[1]})"

        # 2. ISNULL(expr1, expr2) -> COALESCE(expr1, expr2)
        if fn_name == "ISNULL" and len(args) == 2:
            return f"COALESCE({args[0]}, {args[1]})"

        # 3. NVL2(expr, val_if_not_null, val_if_null) -> CASE WHEN expr IS NOT NULL THEN val1 ELSE val2 END
        if fn_name == "NVL2" and len(args) == 3:
            return f"CASE WHEN {args[0]} IS NOT NULL THEN {args[1]} ELSE {args[2]} END"

        # 4. DECODE(col, val1, res1, val2, res2, ..., default) -> CASE WHEN col = val1 THEN res1 ... ELSE default END
        if fn_name == "DECODE" and len(args) >= 3:
            base_col = args[0]
            pairs = args[1:]
            when_clauses = []
            else_clause = "NULL"
            
            idx = 0
            while idx + 1 < len(pairs):
                val = pairs[idx]
                res = pairs[idx + 1]
                when_clauses.append(f"WHEN {base_col} = {val} THEN {res}")
                idx += 2
            if idx < len(pairs):
                else_clause = pairs[idx]

            return f"CASE {' '.join(when_clauses)} ELSE {else_clause} END"

        # 5. INSTR(str, substr) -> POSITION(substr IN str) for PostgreSQL
        if fn_name == "INSTR" and len(args) == 2 and target_dialect in ("POSTGRESQL", "POSTGRES"):
            return f"POSITION({args[1]} IN {args[0]})"

        # 6. LEN(str) -> LENGTH(str) for PostgreSQL/Oracle
        if fn_name == "LEN" and len(args) == 1 and target_dialect in ("POSTGRESQL", "ORACLE"):
            return f"LENGTH({args[0]})"

        return None

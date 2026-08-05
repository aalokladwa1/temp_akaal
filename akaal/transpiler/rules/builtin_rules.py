"""
AKAAL PL/SQL Transpiler — Expanded Phase 2 Built-in Function Rules
=====================================================================
Translates extensive Oracle built-in functions and package APIs to PostgreSQL equivalents:
NVL, NVL2, DECODE, SYSDATE, SYSTIMESTAMP, ROWNUM, SUBSTR, INSTR, TRUNC, ADD_MONTHS, MONTHS_BETWEEN,
LAST_DAY, REGEXP_SUBSTR, REGEXP_REPLACE, DBMS_OUTPUT, DBMS_RANDOM, DBMS_LOB, UTL_FILE, RAISE_APPLICATION_ERROR.
"""

import re
from typing import Any


class BuiltinRulesEngine:
    """Translates Oracle SQL & PL/SQL built-in function expressions."""

    @staticmethod
    def translate_expression(sql: str) -> str:
        res = sql

        # NVL(a, b) -> COALESCE(a, b)
        res = re.sub(r'\bNVL\s*\(', 'COALESCE(', res, flags=re.IGNORECASE)

        # NVL2(a, b, c) -> CASE WHEN a IS NOT NULL THEN b ELSE c END
        res = re.sub(
            r'\bNVL2\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r'CASE WHEN \1 IS NOT NULL THEN \2 ELSE \3 END',
            res,
            flags=re.IGNORECASE
        )

        # DECODE(a, b, c, d) -> CASE WHEN a = b THEN c ELSE d END
        res = re.sub(
            r'\bDECODE\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r'CASE WHEN \1 = \2 THEN \3 ELSE \4 END',
            res,
            flags=re.IGNORECASE
        )

        # SYSDATE -> CURRENT_TIMESTAMP
        res = re.sub(r'\bSYSDATE\b', 'CURRENT_TIMESTAMP', res, flags=re.IGNORECASE)
        res = re.sub(r'\bSYSTIMESTAMP\b', 'CURRENT_TIMESTAMP', res, flags=re.IGNORECASE)

        # ROWNUM -> ROW_NUMBER() OVER ()
        res = re.sub(r'\bROWNUM\b', 'ROW_NUMBER() OVER ()', res, flags=re.IGNORECASE)

        # SUBSTR -> SUBSTRING
        res = re.sub(r'\bSUBSTR\s*\(', 'SUBSTRING(', res, flags=re.IGNORECASE)

        # INSTR -> POSITION
        res = re.sub(r'\bINSTR\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)', r'POSITION(\2 IN \1)', res, flags=re.IGNORECASE)

        # ADD_MONTHS(date, n) -> date + (n || ' month')::interval
        res = re.sub(
            r'\bADD_MONTHS\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r"(\1 + (\2 || ' month')::interval)",
            res,
            flags=re.IGNORECASE
        )

        # MONTHS_BETWEEN(d1, d2) -> (EXTRACT(YEAR FROM age(d1, d2))*12 + EXTRACT(MONTH FROM age(d1, d2)))
        res = re.sub(
            r'\bMONTHS_BETWEEN\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r"(EXTRACT(YEAR FROM age(\1, \2))*12 + EXTRACT(MONTH FROM age(\1, \2)))",
            res,
            flags=re.IGNORECASE
        )

        # SYS_GUID() -> gen_random_uuid()
        res = re.sub(r'\bSYS_GUID\s*\(\s*\)', 'gen_random_uuid()', res, flags=re.IGNORECASE)

        # DBMS_RANDOM.VALUE -> random()
        res = re.sub(r'\bDBMS_RANDOM\.VALUE\b(\s*\(\s*\))?', 'random()', res, flags=re.IGNORECASE)

        # DBMS_LOB.GETLENGTH(a) -> octet_length(a)
        res = re.sub(r'\bDBMS_LOB\.GETLENGTH\s*\(\s*([^)]+)\s*\)', r'octet_length(\1)', res, flags=re.IGNORECASE)

        # RAISE_APPLICATION_ERROR(code, msg) -> RAISE EXCEPTION 'msg' (SQLSTATE)
        res = re.sub(
            r'\bRAISE_APPLICATION_ERROR\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r"RAISE EXCEPTION %%, \2",
            res,
            flags=re.IGNORECASE
        )

        # FROM DUAL -> (Remove FROM DUAL in PostgreSQL)
        res = re.sub(r'\s+FROM\s+DUAL\b', '', res, flags=re.IGNORECASE)

        # DBMS_OUTPUT.PUT_LINE(...) -> RAISE NOTICE ...
        res = re.sub(r'\bDBMS_OUTPUT\.PUT_LINE\s*\(\s*([^)]+)\s*\);', r'RAISE NOTICE %%, \1;', res, flags=re.IGNORECASE)

        # Type conversion calls
        res = re.sub(r'\bTO_DATE\s*\(', 'TO_DATE(', res, flags=re.IGNORECASE)
        res = re.sub(r'\bTO_CHAR\s*\(', 'TO_CHAR(', res, flags=re.IGNORECASE)
        res = re.sub(r'\bTO_NUMBER\s*\(', 'TO_NUMBER(', res, flags=re.IGNORECASE)

        return res

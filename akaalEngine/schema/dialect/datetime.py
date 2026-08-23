"""
akaalEngine.schema.dialect.datetime
===================================
Date/Time arithmetic, interval normalization, and temporal dialect translation.
"""

from __future__ import annotations

import re


class DateTimeDialectTranslator:
    """Translates temporal expressions, date arithmetic, and interval syntax."""

    @classmethod
    def translate_datetime_expression(cls, expr: str, source_dialect: str, target_dialect: str) -> str:
        src = source_dialect.strip().upper()
        tgt = target_dialect.strip().upper()

        if not expr or src == tgt:
            return expr

        result = expr

        # 1. SYSDATE & SYSTIMESTAMP (Oracle -> PostgreSQL / others)
        if src == "ORACLE":
            if tgt in ("POSTGRESQL", "POSTGRES"):
                # Handle SYSDATE + <num> (Oracle day arithmetic)
                result = re.sub(r"\bSYSDATE\s*\+\s*(\d+)", r"CURRENT_TIMESTAMP + INTERVAL '\1 DAY'", result, flags=re.IGNORECASE)
                result = re.sub(r"\bSYSDATE\s*\-\s*(\d+)", r"CURRENT_TIMESTAMP - INTERVAL '\1 DAY'", result, flags=re.IGNORECASE)
                result = re.sub(r"\bSYSDATE\b", "CURRENT_TIMESTAMP", result, flags=re.IGNORECASE)
                result = re.sub(r"\bSYSTIMESTAMP\b", "CURRENT_TIMESTAMP", result, flags=re.IGNORECASE)

        # 2. GETDATE() / SYSDATETIME() (MSSQL -> PostgreSQL / others)
        elif src in ("MSSQL", "SQLSERVER"):
            if tgt in ("POSTGRESQL", "POSTGRES"):
                result = re.sub(r"\bGETDATE\(\)", "CURRENT_TIMESTAMP", result, flags=re.IGNORECASE)
                result = re.sub(r"\bSYSDATETIME\(\)", "CURRENT_TIMESTAMP", result, flags=re.IGNORECASE)
                # DATEADD(day, n, date)
                match_add = re.search(r"DATEADD\s*\(\s*(day|month|year|hour|minute|second)\s*,\s*(\d+)\s*,\s*([^)]+)\)", result, re.IGNORECASE)
                if match_add:
                    unit, amount, base = match_add.groups()
                    result = result.replace(match_add.group(0), f"{base.strip()} + INTERVAL '{amount} {unit.upper()}'")

        # 3. NOW() (MySQL -> PostgreSQL / Snowflake / others)
        elif src in ("MYSQL", "MARIADB"):
            if tgt == "SNOWFLAKE":
                result = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP()", result, flags=re.IGNORECASE)

        return result

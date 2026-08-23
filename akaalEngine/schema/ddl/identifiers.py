"""
akaalEngine.schema.ddl.identifiers
==================================
Target database identifier quoting, escaping, case-folding, length clamping,
and deterministic collision-avoidance hashing.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional


class IdentifierSanitizer:
    """Sanitizes identifiers according to target database vendor rules."""

    # Maximum identifier lengths per engine
    MAX_LENGTHS = {
        "ORACLE": 30,  # Oracle 12.1 and earlier is 30, 12.2+ is 128
        "POSTGRESQL": 63,
        "POSTGRES": 63,
        "MYSQL": 64,
        "MARIADB": 64,
        "MSSQL": 128,
        "SQLSERVER": 128,
        "IBM_DB2": 128,
        "DB2": 128,
        "SQLITE": 255,
        "SNOWFLAKE": 255,
        "BIGQUERY": 1024,
        "REDSHIFT": 127,
        "DATABRICKS": 255,
        "CASSANDRA": 48,
        "SCYLLADB": 48,
    }

    @classmethod
    def sanitize_identifier(
        cls,
        name: str,
        target_engine: str,
        max_length: Optional[int] = None,
        force_lowercase: bool = False,
        force_uppercase: bool = False,
    ) -> str:
        """Sanitizes an identifier: folds case, clamps length, and appends hash on collision/overflow."""
        eng = target_engine.strip().upper()
        limit = max_length or cls.MAX_LENGTHS.get(eng, 63)
        clean = name.strip().replace('"', '').replace('`', '').replace('[', '').replace(']', '')

        # Apply case folding
        if force_lowercase or eng in ("POSTGRESQL", "POSTGRES", "REDSHIFT"):
            clean = clean.lower()
        elif force_uppercase or eng in ("ORACLE", "SNOWFLAKE", "IBM_DB2", "DB2"):
            clean = clean.upper()

        if len(clean) <= limit:
            return clean

        # Deterministic truncation with 8-character hex hash to prevent collisions
        hash_suffix = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        if force_uppercase or eng in ("ORACLE", "SNOWFLAKE", "IBM_DB2", "DB2"):
            hash_suffix = hash_suffix.upper()
        allowed_prefix_len = limit - 9  # underscore + 8 hex chars
        prefix = clean[:max(allowed_prefix_len, 1)]
        return f"{prefix}_{hash_suffix}"

    @classmethod
    def quote_identifier(cls, name: str, target_engine: str) -> str:
        """Quotes an identifier using the appropriate vendor quoting character."""
        eng = target_engine.strip().upper()
        clean = name.strip()

        # MSSQL uses square brackets [table_name]
        if eng in ("MSSQL", "SQLSERVER"):
            if clean.startswith("[") and clean.endswith("]"):
                return clean
            # Escape inner right brackets
            escaped = clean.replace("]", "]]")
            return f"[{escaped}]"

        # MySQL / MariaDB / BigQuery use backticks `table_name`
        elif eng in ("MYSQL", "MARIADB", "BIGQUERY"):
            if clean.startswith("`") and clean.endswith("`"):
                return clean
            escaped = clean.replace("`", "``")
            return f"`{escaped}`"

        # PostgreSQL, Oracle, Snowflake, Redshift, Db2, SQLite use double quotes "table_name"
        else:
            if clean.startswith('"') and clean.endswith('"'):
                return clean
            escaped = clean.replace('"', '""')
            return f'"{escaped}"'

    @classmethod
    def format_qualified_name(cls, schema_name: Optional[str], object_name: str, target_engine: str) -> str:
        """Quotes and joins schema and object name."""
        q_obj = cls.quote_identifier(cls.sanitize_identifier(object_name, target_engine), target_engine)
        if schema_name and schema_name.strip():
            q_schema = cls.quote_identifier(cls.sanitize_identifier(schema_name.strip(), target_engine), target_engine)
            return f"{q_schema}.{q_obj}"
        return q_obj

"""
Akaal — Oracle PL/SQL to PostgreSQL Rewrite Rules
==================================================
Defines type translation, operator mapping, and built-in routine rewrites.
"""

from typing import Dict, Optional

class ProcedureRuleRegistry:
    # Standard Oracle data type conversion mappings to PostgreSQL
    TYPE_MAP = {
        "VARCHAR2": "VARCHAR",
        "NVARCHAR2": "VARCHAR",
        "VARCHAR": "VARCHAR",
        "CHAR": "CHAR",
        "NCHAR": "CHAR",
        "NUMBER": "NUMERIC",
        "BINARY_INTEGER": "INTEGER",
        "PLS_INTEGER": "INTEGER",
        "CLOB": "TEXT",
        "BLOB": "BYTEA",
        "RAW": "BYTEA",
        "DATE": "TIMESTAMP",
        "TIMESTAMP": "TIMESTAMP",
        "FLOAT": "DOUBLE PRECISION",
        "DOUBLE PRECISION": "DOUBLE PRECISION",
        "XMLTYPE": "XML"
    }

    @classmethod
    def map_datatype(cls, oracle_type: str) -> str:
        upper_type = oracle_type.upper().strip()
        
        # Strip precision/scale bounds for baseline lookup, e.g. VARCHAR2(100)
        base_type = upper_type
        suffix = ""
        if "(" in upper_type:
            parts = upper_type.split("(")
            base_type = parts[0].strip()
            suffix = "(" + parts[1]

        mapped_base = cls.TYPE_MAP.get(base_type, base_type)
        return f"{mapped_base}{suffix}"

    @classmethod
    def map_operator(cls, op: str) -> str:
        if op == "!=":
            return "<>"
        return op

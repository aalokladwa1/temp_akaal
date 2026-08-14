"""
AKAAL Enterprise Platform — Compatibility Layer
================================================
Centralizes version-specific SQL dialects, capabilities, feature matrixes, and query syntax
for Oracle (11g, 12c, 19c, 21c), PostgreSQL (12-16), MySQL (5.7, 8.0+), and SQL Server (2016-2022).
"""

from typing import Any, Dict, List
from akaal.core.models.enums import SystemType


class CompatibilityLayer:
    """Centralized database engine dialect & compatibility authority."""

    @staticmethod
    def get_version_capabilities(system_type: SystemType, version_str: str) -> Dict[str, Any]:
        version = version_str.lower()
        if system_type == SystemType.ORACLE:
            return {
                "supports_identity_columns": "12c" in version or "19c" in version or "21c" in version,
                "supports_json_type": "19c" in version or "21c" in version,
                "lob_fetch_method": "locator_stream" if "19c" in version else "inline_chunk",
                "max_varchar_length": 32767 if "12c" in version or "19c" in version else 4000,
            }
        elif system_type == SystemType.POSTGRESQL:
            return {
                "supports_identity_columns": True,
                "supports_jsonb": True,
                "supports_merge_statement": "15" in version or "16" in version,
                "max_identifier_length": 63,
            }
        elif system_type == SystemType.MYSQL:
            return {
                "supports_cte": "8.0" in version,
                "supports_check_constraints": "8.0" in version,
                "max_identifier_length": 64,
            }
        else:
            return {
                "supports_identity_columns": True,
                "max_identifier_length": 128,
            }

    @staticmethod
    def map_datatype(source_type: SystemType, target_type: SystemType, column_type: str) -> str:
        from akaal.schema.domain.type_registry import CanonicalTypeRegistry
        src_name = getattr(source_type, "name", str(source_type))
        tgt_name = getattr(target_type, "name", str(target_type))
        emission = CanonicalTypeRegistry.convert_type(src_name, tgt_name, column_type)
        return emission.target_native_type

    @staticmethod
    def format_quote_identifier(system_type: SystemType, identifier: str) -> str:
        if system_type == SystemType.POSTGRESQL:
            return f'"{identifier.lower()}"'
        elif system_type == SystemType.ORACLE:
            return f'"{identifier.upper()}"'
        elif system_type == SystemType.MYSQL:
            return f'`{identifier}`'
        else:
            return f'[{identifier}]'

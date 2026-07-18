"""
Akaal — Relational Storage Model Family Provider
================================================
Normalizes Relational storage engine types (PostgreSQL, MySQL, Oracle, SQL Server, etc.).
"""

from typing import Dict
from akaal.decoder.providers.base_provider import BaseDecoderProvider
from akaal.decoder.registry.storage_hierarchy import StorageModel
from akaal.decoder.models.canonical_type import CanonicalType, CanonicalTypeFamily


class RelationalDecoderProvider(BaseDecoderProvider):
    provider_id = "relational_family_pack"
    provider_name = "Relational Storage Family Provider"
    semantic_version = "1.0.0"
    supported_storage_model = StorageModel.RELATIONAL
    supported_engine = "RELATIONAL"

    def type_mappings(self) -> Dict[str, CanonicalType]:
        return {
            "integer": CanonicalType(family=CanonicalTypeFamily.INTEGER, name="INTEGER"),
            "bigint": CanonicalType(family=CanonicalTypeFamily.INTEGER, name="BIGINT", parameters={"bytes": 8}),
            "smallint": CanonicalType(family=CanonicalTypeFamily.INTEGER, name="SMALLINT", parameters={"bytes": 2}),
            "numeric": CanonicalType(family=CanonicalTypeFamily.DECIMAL, name="DECIMAL"),
            "decimal": CanonicalType(family=CanonicalTypeFamily.DECIMAL, name="DECIMAL"),
            "varchar": CanonicalType(family=CanonicalTypeFamily.UNICODE_STRING, name="UNICODE_STRING"),
            "varchar2": CanonicalType(family=CanonicalTypeFamily.UNICODE_STRING, name="UNICODE_STRING"),
            "text": CanonicalType(family=CanonicalTypeFamily.UNICODE_STRING, name="UNICODE_STRING"),
            "boolean": CanonicalType(family=CanonicalTypeFamily.BOOLEAN, name="BOOLEAN"),
            "date": CanonicalType(family=CanonicalTypeFamily.DATE, name="DATE"),
            "timestamp": CanonicalType(family=CanonicalTypeFamily.TIMESTAMP, name="TIMESTAMP"),
            "json": CanonicalType(family=CanonicalTypeFamily.JSON, name="JSON"),
            "jsonb": CanonicalType(family=CanonicalTypeFamily.JSON, name="JSON"),
            "uuid": CanonicalType(family=CanonicalTypeFamily.UUID, name="UUID"),
            "bytea": CanonicalType(family=CanonicalTypeFamily.BINARY, name="BINARY"),
            "blob": CanonicalType(family=CanonicalTypeFamily.LARGE_OBJECT, name="LARGE_OBJECT"),
        }

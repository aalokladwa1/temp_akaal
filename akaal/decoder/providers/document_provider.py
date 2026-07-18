"""
Akaal — Document Storage Model Family Provider
==============================================
Normalizes Document storage engine types (MongoDB, Couchbase, etc.).
"""

from typing import Dict
from akaal.decoder.providers.base_provider import BaseDecoderProvider
from akaal.decoder.registry.storage_hierarchy import StorageModel
from akaal.decoder.models.canonical_type import CanonicalType, CanonicalTypeFamily


class DocumentDecoderProvider(BaseDecoderProvider):
    provider_id = "document_family_pack"
    provider_name = "Document Storage Family Provider"
    semantic_version = "1.0.0"
    supported_storage_model = StorageModel.DOCUMENT
    supported_engine = "DOCUMENT"

    def type_mappings(self) -> Dict[str, CanonicalType]:
        return {
            "object": CanonicalType(family=CanonicalTypeFamily.JSON, name="DOCUMENT_OBJECT"),
            "array": CanonicalType(family=CanonicalTypeFamily.ARRAY, name="DOCUMENT_ARRAY"),
            "objectId": CanonicalType(family=CanonicalTypeFamily.UUID, name="DOCUMENT_OBJECT_ID"),
            "string": CanonicalType(family=CanonicalTypeFamily.UNICODE_STRING, name="UNICODE_STRING"),
            "int": CanonicalType(family=CanonicalTypeFamily.INTEGER, name="INTEGER"),
            "double": CanonicalType(family=CanonicalTypeFamily.DECIMAL, name="DECIMAL"),
            "bool": CanonicalType(family=CanonicalTypeFamily.BOOLEAN, name="BOOLEAN"),
            "date": CanonicalType(family=CanonicalTypeFamily.TIMESTAMP, name="TIMESTAMP"),
            "binData": CanonicalType(family=CanonicalTypeFamily.BINARY, name="BINARY"),
        }

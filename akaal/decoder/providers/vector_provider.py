"""
Akaal — Vector Storage Model Family Provider
============================================
Normalizes Vector storage engine types (Milvus, Pinecone, Weaviate, etc.).
"""

from typing import Dict
from akaal.decoder.providers.base_provider import BaseDecoderProvider
from akaal.decoder.registry.storage_hierarchy import StorageModel
from akaal.decoder.models.canonical_type import CanonicalType, CanonicalTypeFamily


class VectorDecoderProvider(BaseDecoderProvider):
    provider_id = "vector_family_pack"
    provider_name = "Vector Storage Family Provider"
    semantic_version = "1.0.0"
    supported_storage_model = StorageModel.VECTOR
    supported_engine = "VECTOR"

    def type_mappings(self) -> Dict[str, CanonicalType]:
        return {
            "float_vector": CanonicalType(family=CanonicalTypeFamily.ARRAY, name="FLOAT_VECTOR", attributes={"element_type": "DECIMAL"}),
            "binary_vector": CanonicalType(family=CanonicalTypeFamily.BINARY, name="BINARY_VECTOR"),
            "sparse_vector": CanonicalType(family=CanonicalTypeFamily.JSON, name="SPARSE_VECTOR"),
        }

"""
Akaal — Graph Storage Model Family Provider
===========================================
Normalizes Graph storage engine types (Neo4j, Neptune, etc.).
"""

from typing import Dict
from akaal.decoder.providers.base_provider import BaseDecoderProvider
from akaal.decoder.registry.storage_hierarchy import StorageModel
from akaal.decoder.models.canonical_type import CanonicalType, CanonicalTypeFamily


class GraphDecoderProvider(BaseDecoderProvider):
    provider_id = "graph_family_pack"
    provider_name = "Graph Storage Family Provider"
    semantic_version = "1.0.0"
    supported_storage_model = StorageModel.GRAPH
    supported_engine = "GRAPH"

    def type_mappings(self) -> Dict[str, CanonicalType]:
        return {
            "node": CanonicalType(family=CanonicalTypeFamily.JSON, name="GRAPH_NODE"),
            "relationship": CanonicalType(family=CanonicalTypeFamily.JSON, name="GRAPH_RELATIONSHIP"),
            "property": CanonicalType(family=CanonicalTypeFamily.UNICODE_STRING, name="GRAPH_PROPERTY"),
        }

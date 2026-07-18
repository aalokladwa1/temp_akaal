"""
Akaal — Warehouse Storage Model Family Provider
===============================================
Normalizes Warehouse storage engine types (Snowflake, BigQuery, Redshift, etc.).
"""

from typing import Dict
from akaal.decoder.providers.base_provider import BaseDecoderProvider
from akaal.decoder.registry.storage_hierarchy import StorageModel
from akaal.decoder.models.canonical_type import CanonicalType, CanonicalTypeFamily


class WarehouseDecoderProvider(BaseDecoderProvider):
    provider_id = "warehouse_family_pack"
    provider_name = "Warehouse Storage Family Provider"
    semantic_version = "1.0.0"
    supported_storage_model = StorageModel.WAREHOUSE
    supported_engine = "WAREHOUSE"

    def type_mappings(self) -> Dict[str, CanonicalType]:
        return {
            "variant": CanonicalType(family=CanonicalTypeFamily.JSON, name="VARIANT"),
            "geography": CanonicalType(family=CanonicalTypeFamily.SPATIAL, name="GEOGRAPHY"),
            "timestamp_tz": CanonicalType(family=CanonicalTypeFamily.TIMESTAMP, name="TIMESTAMP_TZ", attributes={"with_timezone": True}),
            "timestamp_ntz": CanonicalType(family=CanonicalTypeFamily.TIMESTAMP, name="TIMESTAMP_NTZ", attributes={"with_timezone": False}),
        }

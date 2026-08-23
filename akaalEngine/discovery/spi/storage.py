"""
akaalEngine.discovery.spi.storage
=================================
Cloud and distributed object storage discovery SPI extension contract.
Covers S3, GCS, Azure Blob, MinIO, and HDFS.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.structure import ObjectStructureFacts
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy


class StorageDiscoveryStrategy(BaseDiscoveryStrategy):
    """SPI interface for object storage datasets and data lakes."""

    @abstractmethod
    def extract_file_embedded_schema(
        self,
        connection: Any,
        spec: EndpointSpec,
        bucket_name: str,
        object_key: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        """Extracts schema fields and types embedded in Parquet/Avro/ORC file footers."""
        ...

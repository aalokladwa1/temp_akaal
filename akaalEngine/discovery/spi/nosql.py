"""
akaalEngine.discovery.spi.nosql
==============================
NoSQL, document, key-value, graph, and search engine discovery SPI contract.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.sampling import InferredDocumentShape
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy


class NoSQLDiscoveryStrategy(BaseDiscoveryStrategy):
    """SPI interface for NoSQL, document, wide-column, key-value, and graph datastores."""

    @abstractmethod
    def infer_document_shape(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        collection_name: str,
        sample_size: int = 100,
    ) -> InferredDocumentShape:
        """Infers polymorphic field shapes by bounded document sampling."""
        ...

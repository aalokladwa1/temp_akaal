"""
akaalEngine.discovery.spi
=========================
Strategy protocols and SPI contracts for Authority #3 Discovery.
"""

from akaalEngine.discovery.spi.nosql import NoSQLDiscoveryStrategy
from akaalEngine.discovery.spi.relational import RelationalDiscoveryStrategy
from akaalEngine.discovery.spi.storage import StorageDiscoveryStrategy
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy
from akaalEngine.discovery.spi.streaming import StreamingDiscoveryStrategy
from akaalEngine.discovery.spi.warehouse import WarehouseDiscoveryStrategy

__all__ = [
    "BaseDiscoveryStrategy",
    "RelationalDiscoveryStrategy",
    "WarehouseDiscoveryStrategy",
    "NoSQLDiscoveryStrategy",
    "StreamingDiscoveryStrategy",
    "StorageDiscoveryStrategy",
]

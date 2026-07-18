"""
Akaal — Scout Cache Package
===========================
"""

from akaal.scout.cache.base_cache import BaseDiscoveryCache
from akaal.scout.cache.memory_cache import InMemoryDiscoveryCache

__all__ = ["BaseDiscoveryCache", "InMemoryDiscoveryCache"]

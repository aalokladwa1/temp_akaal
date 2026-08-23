"""
akaalEngine.discovery.core
==========================
Core execution and safety engine for Authority #3 Discovery.
"""

from akaalEngine.discovery.core.cache import (
    ProcessLocalDiscoveryCache,
    default_discovery_cache,
)
from akaalEngine.discovery.core.coordinator import (
    DiscoverySessionCoordinator,
)
from akaalEngine.discovery.core.drift import (
    DiscoveryDriftReport,
    DiscoveryDriftSeverity,
    MetadataDriftDetector,
)
from akaalEngine.discovery.core.executor import (
    DiscoveryPipelineExecutor,
)
from akaalEngine.discovery.core.fingerprint import (
    DiscoveryFingerprintCalculator,
)
from akaalEngine.discovery.core.paginator import (
    CatalogPaginator,
    DiscoveryCursor,
)
from akaalEngine.discovery.core.sampling import (
    DeterministicSampler,
    RedactionGuard,
)

__all__ = [
    "DiscoverySessionCoordinator",
    "DiscoveryFingerprintCalculator",
    "ProcessLocalDiscoveryCache",
    "default_discovery_cache",
    "CatalogPaginator",
    "DiscoveryCursor",
    "RedactionGuard",
    "DeterministicSampler",
    "DiscoveryDriftSeverity",
    "DiscoveryDriftReport",
    "MetadataDriftDetector",
    "DiscoveryPipelineExecutor",
]

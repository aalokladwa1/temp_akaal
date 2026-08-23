"""
akaalEngine.extensions.resolution
=================================
Strategy resolution, ambiguity handling, generation-aware caching, and immutable execution handles.
"""

from akaalEngine.extensions.resolution.handles import (
    ResolvedStrategyHandle,
)
from akaalEngine.extensions.resolution.selection import (
    StrategySelector,
)
from akaalEngine.extensions.resolution.cache import (
    ResolutionCache,
    default_resolution_cache,
)
from akaalEngine.extensions.resolution.resolver import (
    StrategyResolver,
    default_strategy_resolver,
)

__all__ = [
    "ResolvedStrategyHandle",
    "StrategySelector",
    "ResolutionCache",
    "default_resolution_cache",
    "StrategyResolver",
    "default_strategy_resolver",
]

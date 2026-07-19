"""
Akaal — Advisor Registry
========================
Registry for discovery, registration, and version lookup of Recommendation Analyzers.
Supports plugin auto-discovery, zero-engine modification extension, thread-safety,
and immutability lifecycle freezing.
"""

import importlib
import pkgutil
import threading
from typing import Dict, List, Optional, Type, Union

from akaal.advisor.analyzers.base_analyzer import RecommendationAnalyzer
from akaal.advisor.analyzers.batch_analyzer import BatchRecommendationAnalyzer
from akaal.advisor.analyzers.best_practice_analyzer import BestPracticeRecommendationAnalyzer
from akaal.advisor.analyzers.checkpoint_analyzer import CheckpointRecommendationAnalyzer
from akaal.advisor.analyzers.cost_analyzer import CostRecommendationAnalyzer
from akaal.advisor.analyzers.eta_analyzer import ETARecommendationAnalyzer
from akaal.advisor.analyzers.hardware_analyzer import HardwareRecommendationAnalyzer
from akaal.advisor.analyzers.parallelism_analyzer import ParallelismRecommendationAnalyzer
from akaal.advisor.analyzers.resource_analyzer import ResourceRecommendationAnalyzer
from akaal.advisor.analyzers.rollback_analyzer import RollbackRecommendationAnalyzer
from akaal.advisor.analyzers.topology_analyzer import TopologyRecommendationAnalyzer
from akaal.advisor.analyzers.worker_analyzer import WorkerRecommendationAnalyzer


class AdvisorRegistryError(Exception):
    """Exception raised for errors in AdvisorRegistry."""
    pass


class AdvisorRegistry:
    """Enterprise Thread-Safe Registry for Advisor Platform Recommendation Analyzers with Lifecycle Freezing."""

    _analyzers: Dict[str, RecommendationAnalyzer] = {}
    _frozen: bool = False
    _lock = threading.RLock()

    @classmethod
    def freeze(cls) -> None:
        """Freeze the registry to prevent further registrations or unregistrations."""
        with cls._lock:
            cls._frozen = True

    @classmethod
    def unfreeze(cls) -> None:
        """Unfreeze the registry for administrative updates."""
        with cls._lock:
            cls._frozen = False

    @classmethod
    def is_frozen(cls) -> bool:
        """Return True if registry is frozen."""
        with cls._lock:
            return cls._frozen

    @classmethod
    def register(
        cls,
        analyzer: Union[RecommendationAnalyzer, Type[RecommendationAnalyzer]],
        name: Optional[str] = None,
    ) -> None:
        """Register an analyzer instance or class thread-safely."""
        with cls._lock:
            if cls._frozen:
                raise AdvisorRegistryError("AdvisorRegistry is frozen. No further registrations are permitted.")

            if isinstance(analyzer, type) and issubclass(analyzer, RecommendationAnalyzer):
                instance = analyzer()
            elif isinstance(analyzer, RecommendationAnalyzer):
                instance = analyzer
            else:
                raise AdvisorRegistryError(
                    f"Cannot register object of type {type(analyzer)}; must inherit from RecommendationAnalyzer."
                )

            reg_name = name or instance.name
            cls._analyzers[reg_name] = instance

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister an analyzer by name thread-safely."""
        with cls._lock:
            if cls._frozen:
                raise AdvisorRegistryError("AdvisorRegistry is frozen. No further unregistrations are permitted.")

            if name in cls._analyzers:
                del cls._analyzers[name]
                return True
            return False

    @classmethod
    def get_analyzer(cls, name: str) -> RecommendationAnalyzer:
        """Get a registered analyzer by name thread-safely."""
        with cls._lock:
            if name not in cls._analyzers:
                raise AdvisorRegistryError(f"Analyzer '{name}' is not registered in AdvisorRegistry.")
            return cls._analyzers[name]

    @classmethod
    def get_all_analyzers(cls) -> List[RecommendationAnalyzer]:
        """Return all currently registered analyzers ordered deterministically by name thread-safely."""
        with cls._lock:
            return [cls._analyzers[k] for k in sorted(cls._analyzers.keys())]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered analyzers thread-safely."""
        with cls._lock:
            if cls._frozen:
                raise AdvisorRegistryError("AdvisorRegistry is frozen. Cannot clear registered analyzers.")
            cls._analyzers.clear()

    @classmethod
    def register_defaults(cls) -> None:
        """Register all 12 core built-in analyzers thread-safely."""
        defaults = [
            BatchRecommendationAnalyzer,
            WorkerRecommendationAnalyzer,
            HardwareRecommendationAnalyzer,
            CostRecommendationAnalyzer,
            ETARecommendationAnalyzer,
            BestPracticeRecommendationAnalyzer,
            CheckpointRecommendationAnalyzer,
            RollbackRecommendationAnalyzer,
            TopologyRecommendationAnalyzer,
            ParallelismRecommendationAnalyzer,
            ResourceRecommendationAnalyzer,
        ]
        with cls._lock:
            if cls._frozen:
                return
            for analyzer_cls in defaults:
                instance = analyzer_cls()
                cls._analyzers[instance.name] = instance

    @classmethod
    def discover_analyzers(cls, package_name: str) -> int:
        """Discover and auto-register analyzers from a target package path thread-safely."""
        count = 0
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            return 0

        if hasattr(package, "__path__"):
            for _, modname, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
                try:
                    mod = importlib.import_module(modname)
                    for item_name in dir(mod):
                        item = getattr(mod, item_name)
                        if (
                            isinstance(item, type)
                            and issubclass(item, RecommendationAnalyzer)
                            and item is not RecommendationAnalyzer
                        ):
                            cls.register(item)
                            count += 1
                except Exception:
                    continue
        return count

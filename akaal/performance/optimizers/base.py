"""
Base Plugin Optimizer Contract for Platform 6.
Every optimizer must implement this common interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from akaal.performance.config.profiles import FeatureFlag


class PluginOptimizer(ABC):
    """Abstract interface for all dynamic execution tune-up plugins."""

    def __init__(self, name: str, flag: FeatureFlag = FeatureFlag.AUTO) -> None:
        self.name = name
        self.flag = flag
        self.version = "1.0.0"

    def update_flag(self, flag: FeatureFlag) -> None:
        self.flag = flag

    def is_enabled(self) -> bool:
        return self.flag in (FeatureFlag.ON, FeatureFlag.AUTO)

    @abstractmethod
    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyzes telemetry metrics and returns optimization parameters.
        Returns None if no optimization changes are recommended.
        """
        pass

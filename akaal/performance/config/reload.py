"""
Enterprise Runtime Configuration Hot Reload Manager.
Atomic, thread-safe dynamic configuration Swapping.
"""

from typing import Dict, Any, Callable, List
from threading import RLock
import logging

from akaal.performance.failures.classification import PerformanceEngineError, PerformanceFailureType

logger = logging.getLogger("nexusforge.performance.config.reload")


class ConfigurationValidator:
    @staticmethod
    def validate(config_data: Dict[str, Any]) -> bool:
        """Enforces schema checking for profiles, thresholds, and limits."""
        if not isinstance(config_data, dict):
            return False
        # Basic validation rules
        if "limits" in config_data and not isinstance(config_data["limits"], dict):
            return False
        if "thresholds" in config_data and not isinstance(config_data["thresholds"], dict):
            return False
        return True


class ConfigurationHotReloader:
    """Orchestrates configuration schema checks and atomic dynamic swapping under lock."""

    def __init__(self, initial_config: Dict[str, Any]) -> None:
        self._lock = RLock()
        self._config = dict(initial_config)
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def register_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def get_config(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._config)

    def hot_reload(self, new_config: Dict[str, Any]) -> None:
        """
        Executes atomic dynamic configuration updates.
        Flow: Validation -> Compatibility Verification -> Hot Reload -> Component Refresh
        """
        if not ConfigurationValidator.validate(new_config):
            raise PerformanceEngineError(
                PerformanceFailureType.CONFIGURATION,
                "Configuration schema validation failed."
            )

        with self._lock:
            # Compatibility checks: prevent invalid overrides
            limits = new_config.get("limits", {})
            if "cpu_percent" in limits and not (0.0 <= limits["cpu_percent"] <= 100.0):
                raise PerformanceEngineError(
                    PerformanceFailureType.CONFIGURATION,
                    "Invalid cpu_percent value in limits."
                )

            # Atomic swap
            self._config = dict(new_config)
            logger.info("Configuration atomic hot reload completed successfully.")

            # Component refresh notification
            for listener in self._listeners:
                try:
                    listener(dict(self._config))
                except Exception as e:
                    logger.error(f"Error executing refresh listener {listener}: {str(e)}", exc_info=True)

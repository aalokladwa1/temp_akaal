"""
Akaal — Intelligence Plugin Infrastructure
===========================================
Implements the plugin manager, lifecycle hooks, version verification,
and dependency-aware registry cleanup tools.
"""

import abc
import logging
from enum import Enum
from typing import Any, Dict, List, Set, Optional

from akaal import __version__ as platform_version
from akaal.core.intelligence.common.exceptions import PluginLoadError
from akaal.core.intelligence.common.models import PluginMetadata
from akaal.core.intelligence.common.registry import BaseRegistry

logger = logging.getLogger("akaal.intelligence.plugin")


class PluginState(str, Enum):
    LOADED = "LOADED"
    ACTIVE = "ACTIVE"
    UNLOADED = "UNLOADED"


class IPlugin(abc.ABC):
    """Abstract interface defining the requirements for custom migration intelligence plugins."""
    @property
    @abc.abstractmethod
    def metadata(self) -> PluginMetadata:
        pass

    @property
    @abc.abstractmethod
    def state(self) -> PluginState:
        pass

    @abc.abstractmethod
    def initialize(self, registries: Dict[str, BaseRegistry[Any]]) -> None:
        """Invoked when loading the plugin. Registers rules and custom strategies."""
        pass

    @abc.abstractmethod
    def teardown(self, registries: Dict[str, BaseRegistry[Any]]) -> None:
        """Invoked when unloading. Safely removes registry entries to prevent leaks."""
        pass


class PluginManager:
    """Manages the lifecycle, load order, dependencies, and cleanups for plugins."""
    def __init__(self, registries: Dict[str, BaseRegistry[Any]]) -> None:
        self._registries = registries
        self._plugins: Dict[str, IPlugin] = {}
        self._plugin_states: Dict[str, PluginState] = {}

    def load_plugin(self, plugin: IPlugin) -> None:
        """Loads, validates, checks dependencies, and initializes a plugin."""
        metadata = plugin.metadata
        plugin_id = metadata.plugin_id

        if plugin_id in self._plugins:
            raise PluginLoadError(
                f"Plugin '{plugin_id}' is already loaded.",
                error_code="PLUGIN_ALREADY_LOADED"
            )

        self._validate_plugin(plugin)
        self._verify_dependencies(metadata)

        # Initialize and register rules
        try:
            plugin.initialize(self._registries)
            self._plugins[plugin_id] = plugin
            self._plugin_states[plugin_id] = PluginState.ACTIVE
            logger.info("Successfully loaded and activated plugin: %s", plugin_id)
        except Exception as e:
            # Safe rollback
            try:
                plugin.teardown(self._registries)
            except Exception:
                pass
            raise PluginLoadError(
                f"Failed to initialize plugin '{plugin_id}': {e}",
                error_code="PLUGIN_INIT_FAILED"
            )

    def unload_plugin(self, plugin_id: str) -> None:
        """Deactivates a plugin and cleans up all registered strategies and rules."""
        if plugin_id not in self._plugins:
            raise PluginLoadError(
                f"Plugin '{plugin_id}' is not active or loaded.",
                error_code="PLUGIN_NOT_FOUND"
            )

        # Check if other active plugins depend on this one
        dependent_plugins = []
        for other_id, other_plugin in self._plugins.items():
            if other_id == plugin_id:
                continue
            if plugin_id in other_plugin.metadata.dependencies:
                dependent_plugins.append(other_id)

        if dependent_plugins:
            raise PluginLoadError(
                f"Cannot unload plugin '{plugin_id}': active plugins {dependent_plugins} depend on it.",
                error_code="PLUGIN_DEPENDENCY_VIOLATION"
            )

        plugin = self._plugins[plugin_id]
        try:
            plugin.teardown(self._registries)
            self._plugin_states[plugin_id] = PluginState.UNLOADED
            del self._plugins[plugin_id]
            logger.info("Successfully unloaded plugin: %s", plugin_id)
        except Exception as e:
            raise PluginLoadError(
                f"Teardown error during unload of plugin '{plugin_id}': {e}",
                error_code="PLUGIN_TEARDOWN_FAILED"
            )

    def get_plugin(self, plugin_id: str) -> Optional[IPlugin]:
        return self._plugins.get(plugin_id)

    def list_active_plugins(self) -> List[IPlugin]:
        return sorted(list(self._plugins.values()), key=lambda p: p.metadata.priority, reverse=True)

    def _validate_plugin(self, plugin: IPlugin) -> None:
        """Verifies plugin interface compatibility and platform version boundaries."""
        metadata = plugin.metadata
        if not metadata.plugin_id or not metadata.version:
            raise PluginLoadError(
                "Invalid plugin metadata: ID and version must be defined.",
                error_code="INVALID_PLUGIN_METADATA"
            )
        # Parse platform versions and compare
        plat_v = platform_version.split(".")
        req_v = metadata.min_platform_version.split(".")
        for p, r in zip(plat_v, req_v):
            try:
                if int(p) < int(r):
                    raise PluginLoadError(
                        f"Plugin '{metadata.plugin_id}' requires platform version {metadata.min_platform_version} (current: {platform_version}).",
                        error_code="PLATFORM_VERSION_INCOMPATIBLE"
                    )
            except ValueError:
                pass

    def _verify_dependencies(self, metadata: PluginMetadata) -> None:
        """Asserts that all requirements specified in dependencies are met."""
        for dep_id in metadata.dependencies:
            if dep_id not in self._plugins:
                raise PluginLoadError(
                    f"Dependency violation: Plugin '{metadata.plugin_id}' requires '{dep_id}' to be loaded first.",
                    error_code="MISSING_PLUGIN_DEPENDENCY"
                )

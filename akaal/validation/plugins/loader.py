"""PluginLoader: Dynamic module loading and instantiation."""

import importlib
import logging
from typing import Any, Optional
from akaal.validation.core.interfaces import IPlugin
from akaal.validation.plugins.registry import PluginRegistry
from akaal.validation.plugins.metadata import PluginMetadata

logger = logging.getLogger("akaal.validation.plugins.loader")


class PluginLoader:
    """Loads Python plugin modules dynamically."""

    def __init__(self, registry: Optional[PluginRegistry] = None):
        self.registry = registry or PluginRegistry()

    def load_from_module_path(self, module_path: str, class_name: str) -> Optional[IPlugin]:
        """Dynamically import a module and instantiate plugin class."""
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            plugin_instance: IPlugin = cls()

            metadata = PluginMetadata(
                plugin_name=plugin_instance.plugin_name,
                entry_point=f"{module_path}:{class_name}",
            )

            self.registry.register_plugin(plugin_instance, metadata)
            logger.info(f"Successfully loaded plugin {plugin_instance.plugin_name}")
            return plugin_instance
        except Exception as exc:
            logger.error(f"Failed to load plugin from {module_path}:{class_name} - {exc}")
            return None

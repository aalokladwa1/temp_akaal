"""
AKAAL Enterprise Platform — Enterprise Plugin Bus
==================================================
Unified hook framework for Validation, Transformation, Notifications, Policies, Reports, Custom Connectors, and Auditing.
"""

from typing import Any, Dict, List, Type
from akaal.core.interfaces.enterprise_interfaces import IPluginBus


class EnterprisePluginBus(IPluginBus):
    """Unified Extension & Plugin Bus."""

    def __init__(self) -> None:
        self._hooks: Dict[str, List[Type]] = {
            "validation": [],
            "transformation": [],
            "cleansing": [],
            "masking": [],
            "notification": [],
            "audit": [],
            "policy": [],
        }

    def register_plugin(self, hook_point: str, plugin_class: Type) -> None:
        if hook_point not in self._hooks:
            self._hooks[hook_point] = []
        if plugin_class not in self._hooks[hook_point]:
            self._hooks[hook_point].append(plugin_class)

    def execute_hooks(self, hook_point: str, context: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(context)
        plugins = self._hooks.get(hook_point, [])
        for plugin_cls in plugins:
            try:
                instance = plugin_cls()
                if hasattr(instance, "process"):
                    res = instance.process(result)
                    if isinstance(res, dict):
                        result.update(res)
            except Exception:
                pass
        return result

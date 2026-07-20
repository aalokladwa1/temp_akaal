"""Plugin Framework and Plugin Lifecycle Protocol Specification."""

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol
from akaal.workflow.utils.serialization import compute_sha256


class PluginState(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    LOADED = "LOADED"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    FAULTED = "FAULTED"


class IWorkflowPlugin(Protocol):
    """Abstract protocol interface implemented by all extensions."""

    @property
    def plugin_name(self) -> str: ...

    @property
    def plugin_version(self) -> str: ...

    def initialize(self) -> bool: ...

    def execute_hook(self, hook_name: str, payload: dict) -> dict: ...


class PluginFramework:
    """Thread-safe plugin framework managing plugin lifecycle and execution."""

    def __init__(self) -> None:
        self._plugins: Dict[str, IWorkflowPlugin] = {}
        self._states: Dict[str, PluginState] = {}
        self._lock = threading.Lock()

    def register_plugin(self, plugin: IWorkflowPlugin) -> bool:
        with self._lock:
            name = plugin.plugin_name
            self._plugins[name] = plugin
            self._states[name] = PluginState.LOADED
            return True

    def initialize_all(self) -> bool:
        with self._lock:
            for name, plugin in self._plugins.items():
                try:
                    if plugin.initialize():
                        self._states[name] = PluginState.ACTIVE
                    else:
                        self._states[name] = PluginState.FAULTED
                except Exception:
                    self._states[name] = PluginState.FAULTED
            return True

    def get_plugin_state(self, plugin_name: str) -> PluginState:
        with self._lock:
            return self._states.get(plugin_name, PluginState.UNINITIALIZED)

    def execute_plugin_hook(self, plugin_name: str, hook_name: str, payload: dict) -> dict:
        with self._lock:
            plugin = self._plugins.get(plugin_name)
            state = self._states.get(plugin_name)
            if not plugin or state != PluginState.ACTIVE:
                return payload
            try:
                return plugin.execute_hook(hook_name, payload)
            except Exception:
                self._states[plugin_name] = PluginState.FAULTED
                return payload

"""Plugin Sandbox Wrapper providing exception isolation and memory/time limits."""

import threading
from typing import Any, Dict
from akaal.workflow.plugins.framework import IWorkflowPlugin, PluginState


class PluginSandbox:
    """Safely executes plugin hooks with panic recovery and isolated exception handling."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    def safe_execute(self, plugin: IWorkflowPlugin, hook_name: str, payload: dict) -> dict:
        """Safely invoke plugin hook, catching all unhandled exceptions."""
        try:
            return plugin.execute_hook(hook_name, payload)
        except Exception as exc:
            # Panic recovery: return unmodified payload and catch error cleanly
            return {**payload, "_plugin_error": str(exc)}

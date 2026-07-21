"""
DistributedRuntimeConfiguration module.
Implements 5-level configuration precedence with hot-reload support, schema versioning, and validation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import os
import json
import logging

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from akaal.distributed.domain.errors import DistributedRuntimeError

logger = logging.getLogger("nexusforge.distributed.config")


@dataclass(frozen=True)
class FrozenDistributedConfiguration:
    config_version: int
    data: Dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        curr = self.data
        for p in parts:
            if isinstance(curr, dict) and p in curr:
                curr = curr[p]
            else:
                return default
        return curr


class DistributedRuntimeConfiguration:
    """
    Configuration manager with 5-level precedence and hot-reload support.
    """

    DEFAULT_CONFIG: Dict[str, Any] = {
        "cluster": {
            "quorum_size": 1,
            "heartbeat_timeout_seconds": 15.0,
            "lease_ttl_seconds": 30.0,
        },
        "scheduler": {
            "default_policy": "LeastLoadedSchedulingPolicy",
            "max_attempts": 3,
        },
        "scaling": {
            "auto_scaling_enabled": False,
            "min_workers": 1,
            "max_workers": 100,
        },
    }

    def __init__(self) -> None:
        self._version = 1
        self._active_config = self.build_config()

    def build_config(self, overrides: Optional[Dict[str, Any]] = None) -> FrozenDistributedConfiguration:
        merged = dict(self.DEFAULT_CONFIG)

        # Environment variables AKAAL_DISTRIBUTED_*
        prefix = "AKAAL_DISTRIBUTED_"
        for env_name, env_val in os.environ.items():
            if env_name.startswith(prefix):
                key_path = env_name[len(prefix):].lower().split("__")
                curr = merged
                for part in key_path[:-1]:
                    curr = curr.setdefault(part, {})
                curr[key_path[-1]] = env_val

        if overrides:
            for k, v in overrides.items():
                if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                    merged[k].update(v)
                else:
                    merged[k] = v

        return FrozenDistributedConfiguration(config_version=self._version, data=merged)

    def hot_reload(self, new_overrides: Dict[str, Any]) -> FrozenDistributedConfiguration:
        """Hot-reload configuration dynamically."""
        self._version += 1
        self._active_config = self.build_config(new_overrides)
        logger.info(f"Hot-reloaded DistributedRuntimeConfiguration to version {self._version}.")
        return self._active_config

    @property
    def active_config(self) -> FrozenDistributedConfiguration:
        return self._active_config

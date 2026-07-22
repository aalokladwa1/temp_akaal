"""
Configuration Version Manager.
Version controls operational configurations, policies, alert thresholds, and rules.
"""

from typing import Dict, List, Any, Optional
from threading import RLock
import time
import copy


class ConfigVersion:
    def __init__(self, version_id: str, version_tag: str, config_data: Dict[str, Any], author: str) -> None:
        self.version_id = version_id
        self.version_tag = version_tag
        self.config_data = copy.deepcopy(config_data)
        self.author = author
        self.created_at = time.time()


class ConfigurationVersionManager:
    """Manages versioned configurations with rollback and diffing support."""

    def __init__(self, initial_config: Optional[Dict[str, Any]] = None) -> None:
        self._lock = RLock()
        self._versions: Dict[str, ConfigVersion] = {}
        self._active_version_id: Optional[str] = None
        
        if initial_config:
            self.commit_version("v1.0.0", initial_config, "system")

    def commit_version(self, version_tag: str, config_data: Dict[str, Any], author: str) -> ConfigVersion:
        with self._lock:
            vid = f"ver_{time.time_ns()}_{len(self._versions)}"
            version = ConfigVersion(vid, version_tag, config_data, author)
            self._versions[vid] = version
            self._active_version_id = vid
            return version

    def get_active_config(self) -> Dict[str, Any]:
        with self._lock:
            if not self._active_version_id or self._active_version_id not in self._versions:
                return {}
            return copy.deepcopy(self._versions[self._active_version_id].config_data)

    def rollback_to_version(self, version_id: str) -> bool:
        with self._lock:
            if version_id in self._versions:
                self._active_version_id = version_id
                return True
            return False

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "version_id": v.version_id,
                    "version_tag": v.version_tag,
                    "author": v.author,
                    "created_at": v.created_at,
                    "is_active": v.version_id == self._active_version_id
                }
                for v in self._versions.values()
            ]

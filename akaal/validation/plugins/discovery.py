"""PluginDiscovery: Directory scanning for custom enterprise plugin packages."""

import os
import glob
from typing import List


class PluginDiscovery:
    """Scans directories for plugin configuration manifests and entry points."""

    def __init__(self, search_paths: List[str] = None):
        self.search_paths = search_paths or ["akaal/validation/plugins/custom"]

    def discover_plugin_files(self) -> List[str]:
        """Find Python plugin files matching *_plugin.py."""
        found_files = []
        for path in self.search_paths:
            if os.path.exists(path):
                pattern = os.path.join(path, "**", "*_plugin.py")
                found_files.extend(glob.glob(pattern, recursive=True))
        return found_files

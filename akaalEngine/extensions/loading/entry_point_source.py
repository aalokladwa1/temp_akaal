"""
akaalEngine.extensions.loading.entry_point_source
=================================================
Discovers and loads extension manifests from Python packaging entry points (group: akaal.extensions).
"""

from __future__ import annotations

import importlib.metadata
import logging
from typing import List, Sequence

from akaalEngine.extensions.errors.taxonomy import ExtensionLoadingError
from akaalEngine.extensions.models.extension import ExtensionManifest

logger = logging.getLogger(__name__)

DEFAULT_ENTRY_POINT_GROUP = "akaal.extensions"


class EntryPointExtensionSource:
    """
    Discovers ExtensionManifest instances declared in installed package entry points.
    """

    @classmethod
    def discover_entry_points(cls, group: str = DEFAULT_ENTRY_POINT_GROUP) -> Sequence[ExtensionManifest]:
        discovered: List[ExtensionManifest] = []

        try:
            eps = importlib.metadata.entry_points(group=group)
        except Exception as exc:
            logger.warning("Failed to query entry points for group '%s': %s", group, exc)
            return ()

        for ep in eps:
            try:
                loaded = ep.load()
                manifest = loaded() if callable(loaded) else loaded
                if isinstance(manifest, ExtensionManifest):
                    discovered.append(manifest)
                else:
                    logger.warning(
                        "Entry point '%s' in group '%s' returned invalid type %s, expected ExtensionManifest.",
                        ep.name,
                        group,
                        type(manifest).__name__,
                    )
            except Exception as exc:
                logger.warning("Failed to load extension entry point '%s': %s", ep.name, exc)

        return tuple(discovered)

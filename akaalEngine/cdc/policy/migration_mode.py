"""
akaalEngine.cdc.policy.migration_mode
=====================================
Deterministic Migration Mode Selector evaluating provider capabilities and prerequisites.
"""

from typing import Any, Dict, Tuple

from akaalEngine.cdc.models.capabilities import CDCCapabilityDescriptor, MigrationMode


class MigrationModeSelector:
    """Selects the strongest valid MigrationMode based on physical provider capabilities."""

    @classmethod
    def select_mode(cls, capability: CDCCapabilityDescriptor, source_config: Dict[str, Any]) -> Tuple[MigrationMode, str]:
        """Returns (selected_mode, reason_explanation)."""
        if capability.capture_mode == MigrationMode.ONLINE_NATIVE_CDC and source_config.get("cdc_enabled", True):
            return MigrationMode.ONLINE_NATIVE_CDC, "Source supports native transaction log CDC"

        if capability.capture_mode == MigrationMode.ONLINE_CHANGE_STREAM:
            return MigrationMode.ONLINE_CHANGE_STREAM, "Source supports Change Stream / oplog capture"

        if capability.capture_mode == MigrationMode.ONLINE_INCREMENTAL:
            return MigrationMode.ONLINE_INCREMENTAL, "Source supports high-watermark timestamp/ID polling"

        return MigrationMode.OFFLINE_SNAPSHOT, "Native CDC prerequisites missing; downgraded to OFFLINE_SNAPSHOT"

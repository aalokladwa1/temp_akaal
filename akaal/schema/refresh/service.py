"""
AKAAL Platform 5 — MetadataRefreshService

Provides automatic, manual, and background metadata refresh capabilities with pub/sub notifications.
"""

from typing import Any, Callable, Dict, Optional
import uuid

from akaal.schema.observability.event_bus import SchemaEventPublisher
from akaal.schema.observability.logger import StructuredAuditLogger
from akaal.schema.refresh.cache import ThreadSafeMetadataCache
from akaal.schema.refresh.coordinator import RefreshCoordinator
from akaal.schema.versioning.manager import MetadataVersionManager
from akaal.schema.versioning.snapshot import SchemaSnapshot


class MetadataRefreshService:
    """Metadata Refresh Service orchestrating live metadata discovery, cache synchronization, and pub/sub events."""

    def __init__(
        self,
        version_manager: MetadataVersionManager,
        cache: Optional[ThreadSafeMetadataCache] = None,
        event_publisher: Optional[SchemaEventPublisher] = None,
        discovery_func: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        self.version_manager = version_manager
        self.cache = cache or ThreadSafeMetadataCache()
        self.coordinator = RefreshCoordinator()
        self.event_publisher = event_publisher or SchemaEventPublisher()
        self.discovery_func = discovery_func
        self.audit_logger = StructuredAuditLogger("akaal.schema.refresh")

    def refresh(self, force: bool = False, priority: int = 5, source: str = "manual") -> Optional[SchemaSnapshot]:
        req_id = f"ref-{uuid.uuid4().hex[:8]}"
        self.coordinator.enqueue_request(req_id, priority=priority, source=source)

        if not self.coordinator.acquire_refresh_lock():
            # Concurrent refresh already in progress, return cached snapshot
            return self.cache.get()

        try:
            if self.discovery_func:
                discovered_tables = self.discovery_func()
            else:
                # Default discovery fallback from version manager repository
                latest = self.version_manager.repository.get_latest()
                discovered_tables = latest.tables if latest else {}

            snapshot = self.version_manager.create_snapshot(
                tables=discovered_tables,
                author=f"refresh-service:{source}",
                commit_message="Live metadata refresh",
            )
            self.cache.put(snapshot)
            self.coordinator.release_refresh_lock(success=True)

            self.event_publisher.publish(
                "METADATA_REFRESHED",
                {"snapshot_id": str(snapshot.snapshot_id), "version_id": str(snapshot.version_id), "source": source},
            )
            self.audit_logger.log_event("METADATA_REFRESH_SUCCESS", details={"version_id": str(snapshot.version_id)})
            return snapshot

        except Exception as e:
            self.coordinator.release_refresh_lock(success=False)
            self.event_publisher.publish("REFRESH_FAILED", {"error": str(e), "source": source})
            self.audit_logger.log_event("METADATA_REFRESH_FAILED", level="ERROR", details={"error": str(e)})
            raise

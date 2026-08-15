"""
AKAAL Safe CDC Schema Transition Barrier.
========================================
Implements safe schema transition barriers preventing events generated under schema version N+1
from being applied under target schema version N. Persists active barriers to CentralStateStore.
"""

from typing import Dict, Any, Optional, Set
import datetime
import logging

from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.positions import CDCSourcePosition
from akaal.cdc.schema_evolution.domain import (
    CDCDDLEvent,
    SchemaTransitionState,
)
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger(__name__)


class CDCSchemaTransitionBarrier:
    """Barrier authority managing active DDL schema barriers per CDC session and table."""

    def __init__(self, state_store: Optional[CentralStateStore] = None) -> None:
        self.state_store = state_store or CentralStateStore()
        self.active_barriers: Dict[str, Dict[str, Any]] = {}  # key: f"{cdc_session_id}:{table_name}"

    def establish_barrier(
        self,
        identity: CDCEventIdentity,
        table_name: str,
        ddl_event: CDCDDLEvent,
        fencing_epoch: int,
    ) -> Dict[str, Any]:
        barrier_key = f"{identity.cdc_session_id}:{table_name}"
        barrier_info = {
            "barrier_id": f"bar-{identity.cdc_session_id}-{ddl_event.ddl_event_id}",
            "identity": identity.to_dict(),
            "table_name": table_name,
            "ddl_event": ddl_event.to_dict(),
            "barrier_position": ddl_event.source_position.to_dict(),
            "old_schema_version_id": ddl_event.old_schema_version_id,
            "proposed_schema_version_id": ddl_event.proposed_schema_version_id,
            "fencing_epoch": fencing_epoch,
            "established_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "is_active": True,
            "state": SchemaTransitionState.BARRIER_ESTABLISHED.value,
        }

        self.active_barriers[barrier_key] = barrier_info
        self.state_store.set_state(f"schema_barrier_{identity.cdc_session_id}_{table_name}", barrier_info, category="schema_barrier")
        logger.info(f"[SchemaBarrier] Established active schema barrier '{barrier_info['barrier_id']}' for table '{table_name}' at position {ddl_event.source_position.to_string()}.")
        return barrier_info

    def is_barrier_active(self, cdc_session_id: str, table_name: str) -> bool:
        barrier_key = f"{cdc_session_id}:{table_name}"
        if barrier_key in self.active_barriers:
            return self.active_barriers[barrier_key].get("is_active", False)

        persisted = self.state_store.get_state(f"schema_barrier_{cdc_session_id}_{table_name}", category="schema_barrier")
        if persisted and persisted.get("is_active"):
            self.active_barriers[barrier_key] = persisted
            return True
        return False

    def release_barrier(
        self,
        cdc_session_id: str,
        table_name: str,
        verified_schema_version_id: str,
        fencing_epoch: Optional[int] = None,
        recovery_coordinator: Optional[Any] = None,
        migration_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        barrier_key = f"{cdc_session_id}:{table_name}"
        if not self.is_barrier_active(cdc_session_id, table_name):
            raise ValueError(f"No active schema barrier to release for session '{cdc_session_id}' table '{table_name}'.")

        barrier_info = self.active_barriers[barrier_key]

        if fencing_epoch is not None and recovery_coordinator is not None and migration_id is not None:
            if not recovery_coordinator.validate_fencing_token(migration_id, fencing_epoch):
                raise ValueError(f"Fencing token violation! Stale epoch {fencing_epoch} rejected during barrier release.")

        if barrier_info["proposed_schema_version_id"] != verified_schema_version_id:
            raise ValueError(f"Cannot release barrier: Verified schema version '{verified_schema_version_id}' does not match proposed '{barrier_info['proposed_schema_version_id']}'.")

        barrier_info["is_active"] = False
        barrier_info["state"] = SchemaTransitionState.COMPLETED.value
        barrier_info["released_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        self.state_store.set_state(f"schema_barrier_{cdc_session_id}_{table_name}", barrier_info, category="schema_barrier")
        logger.info(f"[SchemaBarrier] Released schema barrier '{barrier_info['barrier_id']}' for table '{table_name}'. CDC apply resumed for version '{verified_schema_version_id}'.")
        return barrier_info

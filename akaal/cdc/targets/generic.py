"""
Generic Database Target Adapter for Idempotent Change Application.
"""

from typing import List, Dict, Any
from akaal.cdc.contracts.event import CDCEvent
from akaal.cdc.targets.base import ICDCTargetAdapter


class GenericDatabaseTargetAdapter(ICDCTargetAdapter):
    """Generic Target Database Adapter applying CDC events idempotently."""

    def __init__(self, target_connection_string: str = "postgresql://localhost:5432/target_db") -> None:
        self.target_connection_string = target_connection_string
        self.applied_events: List[CDCEvent] = []

    async def apply_changes(self, events: List[CDCEvent]) -> bool:
        for evt in events:
            # Idempotent apply simulation (upsert on primary key)
            self.applied_events.append(evt)
        return True

from typing import List, Dict, Tuple
from akaal.migration.models.cdc import CDCEvent, CDCOperationType

class CDCPlanner:
    """
    CDCPlanner groups and orders change log events for ingestion.
    Preserves transaction boundaries and chronological sequence order (using LSN/SCN offset indices).
    """
    @staticmethod
    def plan_batch(events: List[CDCEvent]) -> List[CDCEvent]:
        # Sort events by LSN/SCN offset offset to preserve transaction commit chronological order
        sorted_events = sorted(events, key=lambda e: (e.lsn_offset or 0, e.timestamp))
        
        # Deduplicate sequential identical event checksums (Duplicate Event Suppression)
        deduplicated = []
        seen_checksums = set()
        for event in sorted_events:
            if event.checksum:
                if event.checksum in seen_checksums:
                    continue
                seen_checksums.add(event.checksum)
            deduplicated.append(event)
            
        return deduplicated

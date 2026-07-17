from typing import List, Optional
from akaal.migration.versioning.models import ObjectVersionSnapshot
from akaal.migration.versioning.version_store import VersionStore

class RollbackLineageException(Exception):
    """Raised when rollback path validation fails."""
    pass

class RollbackManager:
    """
    Reconstructs lineage paths and validates dependencies/checksum states for rollbacks.
    """
    def __init__(self, store: VersionStore):
        self.store = store

    def reconstruct_rollback_lineage(self, target_version_id: str) -> List[ObjectVersionSnapshot]:
        """
        Walks backwards from the target_version_id to reconstruct the lineage sequence.
        """
        lineage = []
        curr = target_version_id
        
        while curr:
            snap = self.store.get(curr)
            if not snap:
                raise RollbackLineageException(f"Missing rollback snapshot ID '{curr}' in version store.")
                
            # Integrity checksum validation
            checksum = self.store.calculate_checksum(snap)
            if snap.metadata.integrity_checksum and snap.metadata.integrity_checksum != checksum:
                raise RollbackLineageException(f"Integrity checksum validation failed during rollback reconstruction for {curr}.")
                
            lineage.append(snap)
            curr = snap.metadata.parent_version_id
            
        return lineage

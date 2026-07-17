from typing import Optional, List, Dict, Any
from akaal.migration.versioning.models import ObjectVersionSnapshot, VersionDiff

class ComparisonEngine:
    """
    Compares schema snapshots A and B, matching by object_id to detect
    CREATED, DELETED, UNCHANGED, RENAMED, and MODIFIED updates.
    """
    @staticmethod
    def compare_snapshots(snap_a: List[ObjectVersionSnapshot], snap_b: List[ObjectVersionSnapshot]) -> List[VersionDiff]:
        lookup_a = {s.metadata.object_id: s for s in snap_a}
        lookup_b = {s.metadata.object_id: s for s in snap_b}
        
        diffs = []
        all_ids = set(lookup_a.keys()).union(lookup_b.keys())
        
        for obj_id in all_ids:
            s_a = lookup_a.get(obj_id)
            s_b = lookup_b.get(obj_id)
            
            if s_a is None:
                # CREATED
                meta = s_b.metadata
                diffs.append(
                    VersionDiff(
                        from_version_id=None,
                        to_version_id=meta.version_id,
                        object_key=meta.object_name,
                        change_type="CREATED",
                        diff_details={"reason": "New object added"}
                    )
                )
            elif s_b is None:
                # DELETED
                meta = s_a.metadata
                diffs.append(
                    VersionDiff(
                        from_version_id=meta.version_id,
                        to_version_id="",
                        object_key=meta.object_name,
                        change_type="DELETED",
                        diff_details={"reason": "Object deleted"}
                    )
                )
            else:
                meta_a = s_a.metadata
                meta_b = s_b.metadata
                
                # Check fingerprint differences
                if meta_a.object_definition_hash != meta_b.object_definition_hash:
                    change = "MODIFIED"
                    if meta_a.object_name != meta_b.object_name:
                        change = "RENAMED"
                    diffs.append(
                        VersionDiff(
                            from_version_id=meta_a.version_id,
                            to_version_id=meta_b.version_id,
                            object_key=meta_b.object_name,
                            change_type=change,
                            diff_details={"fingerprint_changed": True}
                        )
                    )
                elif meta_a.object_name != meta_b.object_name:
                    diffs.append(
                        VersionDiff(
                            from_version_id=meta_a.version_id,
                            to_version_id=meta_b.version_id,
                            object_key=meta_b.object_name,
                            change_type="RENAMED",
                            diff_details={"reason": "Renamed only"}
                        )
                    )
                else:
                    diffs.append(
                        VersionDiff(
                            from_version_id=meta_a.version_id,
                            to_version_id=meta_b.version_id,
                            object_key=meta_b.object_name,
                            change_type="UNCHANGED"
                        )
                    )
        return diffs

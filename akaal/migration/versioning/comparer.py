from typing import Optional, Dict, Any
from akaal.migration.versioning.models import ObjectVersionSnapshot, VersionDiff

class ObjectVersionComparer:
    """Performs granular comparisons between object states, identifying diff categories."""
    def compare(self, v1: Optional[ObjectVersionSnapshot], v2: ObjectVersionSnapshot) -> VersionDiff:
        if v1 is None:
            return VersionDiff(
                from_version_id=None,
                to_version_id=v2.metadata.version_id,
                object_key=v2.metadata.object_name,
                change_type="CREATE",
                diff_details={"reason": "Initial snapshot creation"}
            )

        v1_meta = v1.metadata
        v2_meta = v2.metadata

        diff_details: Dict[str, Any] = {}
        change_type = "NONE"

        if v1_meta.fingerprint != v2_meta.fingerprint:
            change_type = "UPDATE"
            diff_details["fingerprint_changed"] = True
            if v1_meta.schema_hash != v2_meta.schema_hash:
                diff_details["schema_changed"] = True
            if v1_meta.ddl_hash != v2_meta.ddl_hash:
                diff_details["ddl_changed"] = True
            if v1_meta.metadata_hash != v2_meta.metadata_hash:
                diff_details["metadata_changed"] = True

        return VersionDiff(
            from_version_id=v1_meta.version_id,
            to_version_id=v2_meta.version_id,
            object_key=v2_meta.object_name,
            change_type=change_type,
            diff_details=diff_details
        )

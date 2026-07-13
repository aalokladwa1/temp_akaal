import hashlib
import json
from typing import Any, Dict, Tuple
from akaal.migration.models import MigrationOperation

def calculate_plan_hash(
    source_database: str,
    target_database: str,
    operations: Tuple[MigrationOperation, ...],
    metadata: Dict[str, Any] = None
) -> str:
    """
    Deterministically computes a SHA-256 hash for a given plan configuration and its operations.
    """
    hasher = hashlib.sha256()

    # Hash database schemas
    hasher.update(source_database.encode("utf-8"))
    hasher.update(target_database.encode("utf-8"))

    # Hash general metadata if present
    if metadata:
        meta_str = json.dumps(metadata, sort_keys=True)
        hasher.update(meta_str.encode("utf-8"))

    # Hash operations sorted by operation_id for stable outcomes
    sorted_ops = sorted(operations, key=lambda op: op.operation_id)
    for op in sorted_ops:
        op_str = (
            f"id:{op.operation_id}|"
            f"type:{op.operation_type.value}|"
            f"key:{op.target_object.object_key}|"
            f"obj_type:{op.target_object.object_type.value}|"
            f"deps:{','.join(sorted(list(op.depends_on)))}|"
            f"stage:{op.stage}|"
            f"priority:{op.priority}|"
            f"lock:{op.requires_lock}|"
            f"parallel:{op.can_parallelize}|"
            f"cost:{op.estimated_cost}"
        )
        hasher.update(op_str.encode("utf-8"))

    return hasher.hexdigest()

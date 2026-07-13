import hashlib
import json
from typing import Any, Dict, Tuple
from akaal.migration.models import MigrationOperation, MigrationObject

def canonicalize_metadata(val: Any) -> Any:
    """
    Recursively canonicalizes nested metadata structures to guarantee determinism.
    Converts sets to sorted lists, handles dict sorting, and filters out dynamic runtime keys.
    """
    excluded_keys = {
        "timestamp", "uuid", "plan_id", "run_id", "session_id", "trace_id",
        "generated_at", "created_at", "updated_at", "duration", "execution_time",
        "execution_order", "memory_address", "random_id", "id", "object_id"
    }
    
    if isinstance(val, dict):
        cleaned = {}
        for k, v in val.items():
            k_lower = str(k).lower().strip()
            # Exclude runtime keys or keys ending with excluded suffixes
            if any(k_lower == ex or k_lower.endswith("_" + ex) for ex in excluded_keys):
                continue
            cleaned[k] = canonicalize_metadata(v)
        return {k: cleaned[k] for k in sorted(cleaned.keys())}
        
    elif isinstance(val, (list, tuple)):
        return tuple(canonicalize_metadata(x) for x in val)
        
    elif isinstance(val, (set, frozenset)):
        canonicalized_items = [canonicalize_metadata(x) for x in val]
        try:
            canonicalized_items.sort()
        except TypeError:
            canonicalized_items.sort(key=str)
        return tuple(canonicalized_items)
        
    elif hasattr(val, "__dict__"):
        return canonicalize_metadata(val.__dict__)
        
    return val

def canonicalize_migration_object(obj: Any) -> Any:
    """
    Strips non-deterministic properties (like randomly generated object_id UUIDs)
    from a MigrationObject and extracts its stable attributes in a canonical dict format.
    """
    if not isinstance(obj, MigrationObject):
        return canonicalize_metadata(obj)
        
    d = {
        "name": obj.name,
        "object_type": obj.object_type.value if hasattr(obj.object_type, "value") else str(obj.object_type),
        "object_key": obj.object_key,
        "schema": obj.schema,
        "vendor_metadata": canonicalize_metadata(obj.vendor_metadata),
        "attributes": canonicalize_metadata(obj.attributes),
    }
    
    # Extract type-specific fields safely
    if hasattr(obj, "data_type"):
        d["data_type"] = obj.data_type
        d["nullable"] = obj.nullable
        d["default"] = obj.default
    if hasattr(obj, "constraint_type"):
        d["constraint_type"] = obj.constraint_type
        d["columns"] = tuple(obj.columns)
        d["reference_table"] = obj.reference_table
        d["reference_columns"] = tuple(obj.reference_columns)
        d["check_clause"] = obj.check_clause
    if hasattr(obj, "unique") and hasattr(obj, "index_type"):
        d["columns"] = tuple(obj.columns)
        d["unique"] = obj.unique
        d["index_type"] = obj.index_type
    if hasattr(obj, "definition"):
        d["definition"] = obj.definition
    if hasattr(obj, "dependencies"):
        d["dependencies"] = tuple(obj.dependencies)
    if hasattr(obj, "refresh_mode"):
        d["refresh_mode"] = obj.refresh_mode
        d["refresh_method"] = obj.refresh_method
    if hasattr(obj, "table_name"):
        d["table_name"] = obj.table_name
    if hasattr(obj, "timing"):
        d["timing"] = obj.timing
        d["event"] = obj.event
    if hasattr(obj, "parameters"):
        d["parameters"] = tuple(canonicalize_metadata(p) for p in obj.parameters)
    if hasattr(obj, "return_type"):
        d["return_type"] = obj.return_type
    if hasattr(obj, "language"):
        d["language"] = obj.language
    if hasattr(obj, "start_value"):
        d["start_value"] = obj.start_value
        d["increment_by"] = obj.increment_by
        d["min_value"] = obj.min_value
        d["max_value"] = obj.max_value
        d["cycle"] = obj.cycle
    if hasattr(obj, "partition_type"):
        d["partition_type"] = obj.partition_type
        d["expression"] = obj.expression
        d["values"] = tuple(obj.values)
    if hasattr(obj, "object_name"):
        d["object_name"] = obj.object_name
    if hasattr(obj, "is_public"):
        d["is_public"] = obj.is_public
        
    return d

def calculate_plan_hash(
    source_database: str,
    target_database: str,
    operations: Tuple[MigrationOperation, ...],
    metadata: Dict[str, Any] = None
) -> str:
    """
    Deterministically computes a SHA-256 hash for a given plan configuration and its operations.
    Ensures dictionary ordering, sets, random UUIDs, or dynamic timestamps do not influence output.
    """
    hasher = hashlib.sha256()

    # Hash database schemas (normalized)
    hasher.update(source_database.strip().encode("utf-8"))
    hasher.update(target_database.strip().encode("utf-8"))

    # Hash metadata (canonicalized, sorted, runtime keys filtered)
    clean_meta = canonicalize_metadata(metadata or {})
    meta_str = json.dumps(clean_meta, sort_keys=True)
    hasher.update(meta_str.encode("utf-8"))

    def get_op_type(o: MigrationOperation) -> str:
        opt = o.operation_type
        return opt.value if hasattr(opt, "value") else str(opt)

    # Sort operations by type and object key to ensure stable hashing order
    sorted_ops = sorted(operations, key=lambda op: (get_op_type(op), op.target_object.object_key))
    
    for op in sorted_ops:
        op_type_val = get_op_type(op)
        # Canonicalize target object semantic properties (omitting object_id)
        canon_obj = canonicalize_migration_object(op.target_object)
        obj_str = json.dumps(canon_obj, sort_keys=True)

        op_str = (
            f"type:{op_type_val}|"
            f"obj:{obj_str}|"
            f"deps:{','.join(sorted(list(op.depends_on)))}|"
            f"stage:{op.stage}|"
            f"priority:{op.priority}|"
            f"lock:{op.requires_lock}|"
            f"parallel:{op.can_parallelize}|"
            f"cost:{op.estimated_cost}|"
            f"meta:{json.dumps(canonicalize_metadata(op.metadata), sort_keys=True)}"
        )
        hasher.update(op_str.encode("utf-8"))

    return hasher.hexdigest()

import hashlib
from akaal.migration.models import MigrationPlan

def generate_plan_hash(plan: MigrationPlan) -> str:
    """Computes a stable SHA-256 checksum for a MigrationPlan to verify execution immutability."""
    if not plan or not plan.operations:
        return hashlib.sha256(b"").hexdigest()
    # Sort operation IDs for deterministic ordering
    sorted_op_ids = sorted(op.operation_id for op in plan.operations)
    payload = f"{plan.plan_version or '1.0'}:" + ",".join(sorted_op_ids)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

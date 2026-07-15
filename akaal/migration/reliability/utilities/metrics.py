from akaal.migration.models import MigrationPlan

def calculate_complexity(plan: MigrationPlan) -> float:
    """Calculates operational complexity score from 0.0 to 10.0 based on plan operations."""
    if not plan or not plan.operations:
        return 0.0
    score = 0.0
    for op in plan.operations:
        # Check metadata fields or operation types
        if getattr(op, "destructive", False):
            score += 2.0
        else:
            score += 0.5
    return min(10.0, score)

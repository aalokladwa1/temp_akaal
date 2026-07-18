"""
Akaal — Execution State Model
=============================
Defines the intended lifecycle state of every ExecutionTask in MigrationExecutionPlan.
Planner defines these states statically without performing execution.
"""

from enum import Enum


class ExecutionState(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    EXECUTING = "EXECUTING"
    CHECKPOINT = "CHECKPOINT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"

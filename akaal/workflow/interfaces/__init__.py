"""Interfaces package for AKAAL Workflow Platform."""

from akaal.workflow.interfaces.base import (
    IStep,
    IExecutionStrategy,
    IEngine,
    IWorkflowLock,
)
from akaal.workflow.utils.clock import IClock
from akaal.workflow.utils.id_generator import IIdGenerator

__all__ = [
    "IStep",
    "IExecutionStrategy",
    "IEngine",
    "IWorkflowLock",
    "IClock",
    "IIdGenerator",
]

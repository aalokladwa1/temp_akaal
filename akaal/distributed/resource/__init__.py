"""
Resource package for Distributed Runtime.
"""

from akaal.distributed.resource.manager import ResourceManager
from akaal.distributed.resource.scaling import WorkerScalingManager

__all__ = ["ResourceManager", "WorkerScalingManager"]

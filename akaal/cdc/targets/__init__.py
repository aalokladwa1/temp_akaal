"""
CDC Targets package initialization.
"""

from akaal.cdc.targets.base import ICDCTargetAdapter
from akaal.cdc.targets.generic import GenericDatabaseTargetAdapter

__all__ = ["ICDCTargetAdapter", "GenericDatabaseTargetAdapter"]

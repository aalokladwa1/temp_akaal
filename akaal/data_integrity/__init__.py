"""
AKAAL Platform 8 — Enterprise Data Integrity Platform Initialization.
"""

from akaal.data_integrity.facade.platform8 import EnterpriseDataIntegrityPlatformV8
from akaal.data_integrity.batch_validator import BatchLevelValidator, BatchValidationResult

__all__ = ["EnterpriseDataIntegrityPlatformV8", "BatchLevelValidator", "BatchValidationResult"]

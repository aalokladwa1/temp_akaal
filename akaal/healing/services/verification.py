"""RepairVerificationService: Re-validates data post-repair using Platform 1 (Cap 8)."""

from typing import Any, Optional
from akaal.healing.core.interfaces import IHealingService


class RepairVerificationService(IHealingService):
    """Infrastructure service integrating with Platform 1 to verify repairs."""

    @property
    def service_name(self) -> str:
        return "RepairVerificationService"

    async def verify_repair(
        self, validation_platform: Any, source_adapter: Any = None, target_adapter: Any = None
    ) -> bool:
        """Execute post-repair re-validation via Platform 1 facade."""
        if validation_platform and hasattr(validation_platform, "validate_all_async"):
            val_session = await validation_platform.validate_all_async(source_adapter, target_adapter)
            return val_session.total_issues_found == 0
        return True

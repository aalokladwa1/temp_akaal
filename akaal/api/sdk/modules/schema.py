"""
SDK SchemaApi Module.
"""

from akaal.api.contracts.dto import SchemaCheckDTO, SchemaCompatibilityResultDTO
from akaal.api.facades.platform5 import Platform5Facade
from akaal.api.resilience.retry import RetryPolicy


class SchemaApi:
    """Async Schema Client for SDK."""

    def __init__(self, facade: Platform5Facade = None) -> None:
        self.facade = facade or Platform5Facade()
        self.retry_policy = RetryPolicy(max_retries=3)

    async def check_compatibility(self, schema_name: str, ddl: str) -> SchemaCompatibilityResultDTO:
        dto = SchemaCheckDTO(target_schema_name=schema_name, proposed_ddl=ddl)
        return await self.retry_policy.execute(self.facade.validate_schema_compatibility, dto)

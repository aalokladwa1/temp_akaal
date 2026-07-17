"""
Akaal — Application Composition Root
====================================
Initializes conversion engine components and resolves service dependencies.
"""

from akaal.core.conversion.api.service import IProcedureConversionService
from akaal.core.conversion.internal.procedure.service_impl import ProcedureConversionService

class Bootstrap:
    """Composition Root for stored routine migration subsystem."""

    @staticmethod
    def initialize_procedure_service() -> IProcedureConversionService:
        """Constructs and returns the configured stored procedure conversion service."""
        # Clean constructor-based injection of underlying rules and resolvers
        return ProcedureConversionService()

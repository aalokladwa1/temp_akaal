"""
Akaal — Application Composition Root
====================================
Initializes conversion engine components and resolves service dependencies.
"""

from akaal.core.conversion.api.service import IProcedureConversionService
from akaal.core.conversion.internal.routine.service_impl import RoutineConversionService

class Bootstrap:
    """Composition Root for stored routine migration subsystem."""

    @staticmethod
    def initialize_procedure_service() -> IProcedureConversionService:
        """Constructs and returns the configured stored routine conversion service."""
        return RoutineConversionService()

    @staticmethod
    def initialize_function_service():
        """Constructs and returns the function conversion service."""
        return RoutineConversionService()


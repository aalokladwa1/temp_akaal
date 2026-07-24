"""
AKAAL Platform 7 — Domain Exception Hierarchy.
"""


class OperationalReliabilityError(Exception):
    """Base exception for Platform 7 Operational Reliability errors."""
    pass


class SLOBreachError(OperationalReliabilityError):
    """Raised when an SLO target is breached."""
    pass


class SLABreachError(OperationalReliabilityError):
    """Raised when an enterprise SLA is violated."""
    pass


class ServiceNotFoundError(OperationalReliabilityError):
    """Raised when a service is not found in the service catalog."""
    pass


class IncidentError(OperationalReliabilityError):
    """Raised when an invalid operation is performed on an incident."""
    pass


class MaintenanceConflictError(OperationalReliabilityError):
    """Raised when a maintenance window conflict occurs."""
    pass

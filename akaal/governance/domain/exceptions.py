"""
AKAAL Platform 6 — Domain Exception Hierarchy.
"""


class GovernanceError(Exception):
    """Base exception for all Platform 6 governance errors."""
    pass


class SoDViolationError(GovernanceError):
    """Raised when Separation of Duties rules are violated."""
    pass


class PolicyViolationError(GovernanceError):
    """Raised when a governance policy check fails."""
    pass


class SLABreachError(GovernanceError):
    """Raised when an approval SLA timeline is breached."""
    pass


class LifecycleValidationError(GovernanceError):
    """Raised when an invalid governance artifact state transition is attempted."""
    pass


class CircularDependencyError(GovernanceError):
    """Raised when a circular dependency is detected in the governance graph."""
    pass


class LedgerTamperError(GovernanceError):
    """Raised when immutable ledger hash chain tampering is detected."""
    pass

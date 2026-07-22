"""
Integration package for AKAAL Platforms 1 through 9.
"""

from akaal.integration.cross_platform import CrossPlatformIntegrationEngine, create_sample_migration_job
from akaal.integration.composition_root import (
    EnterpriseLifecycleManager,
    PlatformRegistry,
    PlatformDescriptor,
    DependencyGraph,
    HealthRegistry,
    CrossPlatformContext,
    execute_e2e_smoke_test,
    EnterpriseCompositionError,
    DuplicatePlatformError,
    MissingPlatformError,
    PlatformValidationFailedError,
    CircularDependencyError,
)

__all__ = [
    "CrossPlatformIntegrationEngine",
    "create_sample_migration_job",
    "EnterpriseLifecycleManager",
    "PlatformRegistry",
    "PlatformDescriptor",
    "DependencyGraph",
    "HealthRegistry",
    "CrossPlatformContext",
    "execute_e2e_smoke_test",
    "EnterpriseCompositionError",
    "DuplicatePlatformError",
    "MissingPlatformError",
    "PlatformValidationFailedError",
    "CircularDependencyError",
]

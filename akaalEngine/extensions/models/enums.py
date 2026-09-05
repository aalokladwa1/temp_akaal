"""
akaalEngine.extensions.models.enums
===================================
Enumerations governing extension origin, trust tiers, isolation modes, lifecycle states, dependency types, and proof levels.
"""

from __future__ import annotations

from enum import Enum


class ExtensionOrigin(str, Enum):
    """Origin source of an extension bundle."""
    BUILTIN = "BUILTIN"                      # Core built-in engine implementation
    LOCAL_WORKSPACE = "LOCAL_WORKSPACE"      # Local development or workspace contribution
    THIRD_PARTY_PACKAGE = "THIRD_PARTY"      # Installed Python package / distribution
    DYNAMIC = "DYNAMIC"                      # Dynamically registered in-memory


class TrustTier(str, Enum):
    """Trust classification for extension security and verification governance."""
    CORE_TRUSTED = "CORE_TRUSTED"            # First-party core engine code
    VERIFIED_PARTNER = "VERIFIED_PARTNER"    # Signed/verified partner implementation
    COMMUNITY = "COMMUNITY"                  # Community / unverified third-party
    UNTRUSTED = "UNTRUSTED"                  # Explicitly restricted execution


class IsolationMode(str, Enum):
    """Truthful declaration of extension execution isolation."""
    IN_PROCESS = "IN_PROCESS"                # Runs in engine Python process
    SUBPROCESS = "SUBPROCESS"                # Real separate-OS-process isolation (P7A.3, akaalEngine.extensions.sandbox)
    WASM_UNSUPPORTED = "WASM"                # WebAssembly sandbox (contract-reserved, no WASM runtime in this repo/environment)
    REMOTE_UNSUPPORTED = "REMOTE"            # Remote gRPC/IPC worker (contract-reserved, no remote worker infrastructure exists)


class ExtensionLifecycleState(str, Enum):
    """Lifecycle states of an extension in the engine."""
    DISCOVERED = "DISCOVERED"                # Found by loader but not yet registered
    REGISTERED = "REGISTERED"                # Validated and registered, awaiting activation
    ACTIVE = "ACTIVE"                        # Active and available for resolution
    INACTIVE = "INACTIVE"                    # Explicitly deactivated; rejects new resolutions, allows active leases to drain
    UNAVAILABLE = "UNAVAILABLE"              # Missing mandatory dependencies or incompatible engine version
    FAULTED = "FAULTED"                      # Runtime failure or verification fault
    REMOVED = "REMOVED"                      # Unregistered and permanently removed from published registry


class ProofLevel(str, Enum):
    """Truthful capability proof tier."""
    DECLARED = "DECLARED"                    # Self-asserted capability in manifest (unproven)
    IMPLEMENTED = "IMPLEMENTED"              # Concrete code exists matching authority contract
    UNIT_PROVEN = "UNIT_PROVEN"              # Verified by automated unit test fixtures
    INTEGRATION_PROVEN = "INTEGRATION_PROVEN"# Verified against isolated integration emulator
    LIVE_PROVEN = "LIVE_PROVEN"              # Certified against physical live target database


class DependencyMatchMode(str, Enum):
    """Evaluation operator for composite dependency groups."""
    ALL_OF = "ALL_OF"                        # All member dependencies must be satisfied
    ANY_OF = "ANY_OF"                        # At least one member dependency must be satisfied


class DependencyType(str, Enum):
    """Classification of external dependency requirements."""
    PYTHON_PACKAGE = "PYTHON_PACKAGE"
    NATIVE_LIBRARY = "NATIVE_LIBRARY"
    EXECUTABLE = "EXECUTABLE"
    SERVICE_ENDPOINT = "SERVICE_ENDPOINT"
    DEPENDENCY_GROUP = "DEPENDENCY_GROUP"


class DependencyStatus(str, Enum):
    """Evaluation status of a dependency requirement."""
    SATISFIED = "SATISFIED"
    MISSING = "MISSING"
    VERSION_MISMATCH = "VERSION_MISMATCH"
    INCOMPATIBLE = "INCOMPATIBLE"
    EVALUATION_ERROR = "EVALUATION_ERROR"


class ConfigurationFieldType(str, Enum):
    """Data types for extension and provider configuration schema fields."""
    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"
    LIST = "LIST"
    OBJECT = "OBJECT"
    SECRET_REF = "SECRET_REF"                # Ephemeral reference to a secret pointer (never raw plaintext)

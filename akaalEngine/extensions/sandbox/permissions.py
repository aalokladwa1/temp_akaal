"""
akaalEngine.extensions.sandbox.permissions
============================================
Requested vs granted permission separation for extension execution.

A PermissionRequest is data an extension manifest asserts about itself -- it carries
no authority. A GrantedPermissions is a distinct type that only an authorization
decision (owned outside this Engine-side module, by the caller's own policy layer)
may construct with a non-empty grant. This module enforces the type separation;
it does not itself decide what should be granted -- that is a policy call belonging
to whichever caller composes Engine with its trust/authorization layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional


class PermissionKind(str, Enum):
    FILESYSTEM_READ = "FILESYSTEM_READ"
    FILESYSTEM_WRITE = "FILESYSTEM_WRITE"
    NETWORK_EGRESS = "NETWORK_EGRESS"
    ENVIRONMENT_VARIABLE = "ENVIRONMENT_VARIABLE"
    SECRET_REFERENCE = "SECRET_REFERENCE"
    HOST_FUNCTION = "HOST_FUNCTION"


class IsolationAssurance(str, Enum):
    """
    Truthful isolation assurance tiers, ordered weakest-to-strongest. HOST_MEDIATED is
    what this Engine can actually provide today (see sandbox/host_mediated.py) --
    extension code never gets ambient filesystem/socket authority, all access is
    validated and brokered by the host process. OS_ENFORCED denotes real kernel-level
    containment (e.g. a restricted token/low-IL process, seccomp/namespaces, a real
    firewall-enforced network boundary) -- NOT implemented anywhere in this Engine as of
    this module. Declaring a requirement of OS_ENFORCED is therefore never satisfiable on
    the current runtime and must be rejected before execution, not silently downgraded.
    """
    HOST_MEDIATED = "HOST_MEDIATED"
    OS_ENFORCED = "OS_ENFORCED"


_ASSURANCE_RANK = {IsolationAssurance.HOST_MEDIATED: 0, IsolationAssurance.OS_ENFORCED: 1}


def assurance_satisfies(available: IsolationAssurance, required: IsolationAssurance) -> bool:
    """True iff `available` is at least as strong as `required`."""
    return _ASSURANCE_RANK[available] >= _ASSURANCE_RANK[required]


def stricter_assurance(a: IsolationAssurance, b: IsolationAssurance) -> IsolationAssurance:
    """Returns whichever of the two requires stronger isolation -- never the weaker of the two."""
    return a if _ASSURANCE_RANK[a] >= _ASSURANCE_RANK[b] else b


@dataclass(frozen=True)
class PermissionRequest:
    """
    Declarative, self-asserted permission request carried on an extension manifest.
    NEVER treated as a grant anywhere in this module or its callers.
    """
    filesystem_read_paths: FrozenSet[str] = field(default_factory=frozenset)
    filesystem_write_paths: FrozenSet[str] = field(default_factory=frozenset)
    network_egress_hosts: FrozenSet[str] = field(default_factory=frozenset)
    environment_variables: FrozenSet[str] = field(default_factory=frozenset)
    secret_references: FrozenSet[str] = field(default_factory=frozenset)
    host_functions: FrozenSet[str] = field(default_factory=frozenset)
    cpu_time_budget_seconds: Optional[float] = None
    memory_budget_bytes: Optional[int] = None
    wall_clock_budget_seconds: Optional[float] = None
    required_filesystem_isolation: IsolationAssurance = IsolationAssurance.HOST_MEDIATED
    required_network_isolation: IsolationAssurance = IsolationAssurance.HOST_MEDIATED

    def __post_init__(self) -> None:
        for name in ("filesystem_read_paths", "filesystem_write_paths", "network_egress_hosts",
                     "environment_variables", "secret_references", "host_functions"):
            object.__setattr__(self, name, frozenset(getattr(self, name)))
        if self.cpu_time_budget_seconds is not None and self.cpu_time_budget_seconds <= 0:
            raise ValueError("cpu_time_budget_seconds must be positive if specified.")
        if self.memory_budget_bytes is not None and self.memory_budget_bytes <= 0:
            raise ValueError("memory_budget_bytes must be positive if specified.")
        if self.wall_clock_budget_seconds is not None and self.wall_clock_budget_seconds <= 0:
            raise ValueError("wall_clock_budget_seconds must be positive if specified.")


@dataclass(frozen=True)
class GrantedPermissions:
    """
    The actual, authoritative set of permissions an extension may exercise at runtime.
    Distinct type from PermissionRequest by design -- code that needs a grant cannot
    accidentally receive a request object instead, since the types are not interchangeable
    and nothing in this module converts one into the other.
    """
    filesystem_read_paths: FrozenSet[str] = field(default_factory=frozenset)
    filesystem_write_paths: FrozenSet[str] = field(default_factory=frozenset)
    network_egress_hosts: FrozenSet[str] = field(default_factory=frozenset)
    environment_variables: FrozenSet[str] = field(default_factory=frozenset)
    secret_references: FrozenSet[str] = field(default_factory=frozenset)
    host_functions: FrozenSet[str] = field(default_factory=frozenset)
    cpu_time_budget_seconds: Optional[float] = None
    memory_budget_bytes: Optional[int] = None
    wall_clock_budget_seconds: Optional[float] = None
    required_filesystem_isolation: IsolationAssurance = IsolationAssurance.HOST_MEDIATED
    required_network_isolation: IsolationAssurance = IsolationAssurance.HOST_MEDIATED

    def __post_init__(self) -> None:
        for name in ("filesystem_read_paths", "filesystem_write_paths", "network_egress_hosts",
                     "environment_variables", "secret_references", "host_functions"):
            object.__setattr__(self, name, frozenset(getattr(self, name)))

    @classmethod
    def empty(cls) -> "GrantedPermissions":
        """The zero-trust default: no filesystem, network, env, secret, or host-function access."""
        return cls()

    @classmethod
    def restrict_to_request(cls, requested: PermissionRequest, approved: PermissionRequest) -> "GrantedPermissions":
        """
        Builds a grant as the intersection of what was requested and what a caller-supplied
        `approved` policy allows -- a grant can never exceed what was actually requested,
        closing the "manifest claims replacing actual grants" escalation path.

        required_*_isolation is the one dimension NOT intersected downward: the effective
        requirement is the STRICTER of what the extension asked for and what the trusted
        policy mandates (`stricter_assurance`), so neither side can weaken the other's
        isolation requirement -- an extension cannot self-declare a weaker need to dodge an
        owner-mandated floor, and an owner policy cannot silently downgrade what an
        extension itself said it needs.
        """
        return cls(
            filesystem_read_paths=requested.filesystem_read_paths & approved.filesystem_read_paths,
            filesystem_write_paths=requested.filesystem_write_paths & approved.filesystem_write_paths,
            network_egress_hosts=requested.network_egress_hosts & approved.network_egress_hosts,
            environment_variables=requested.environment_variables & approved.environment_variables,
            secret_references=requested.secret_references & approved.secret_references,
            host_functions=requested.host_functions & approved.host_functions,
            cpu_time_budget_seconds=cls._min_optional(requested.cpu_time_budget_seconds, approved.cpu_time_budget_seconds),
            memory_budget_bytes=cls._min_optional(requested.memory_budget_bytes, approved.memory_budget_bytes),
            wall_clock_budget_seconds=cls._min_optional(requested.wall_clock_budget_seconds, approved.wall_clock_budget_seconds),
            required_filesystem_isolation=stricter_assurance(
                requested.required_filesystem_isolation, approved.required_filesystem_isolation
            ),
            required_network_isolation=stricter_assurance(
                requested.required_network_isolation, approved.required_network_isolation
            ),
        )

    @staticmethod
    def _min_optional(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None:
            return b
        if b is None:
            return a
        return min(a, b)

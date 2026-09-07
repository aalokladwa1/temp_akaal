"""
akaalEngine.fabric.placement.residency
=========================================
P7B.15 -- Locality & Data-Sovereignty Enforcement.

Evaluates a `ResidencyPolicy` against the ENTIRE movement path (source, network hops,
relay, staging, execution site, target, and optionally the validation/evidence
destination) -- never only the two endpoints. Built entirely on top of
akaalEngine.fabric.locality.models.LocalityRecord.satisfies(), which already refuses to
answer True/False for anything not PROVEN and fresh -- this module's only additional
responsibility is composing that per-record three-valued answer across every required
role in the path and failing closed the moment ANY of them is non-compliant or unknown.

ABSOLUTE LAW:

    UNKNOWN LOCALITY CANNOT SATISFY A POLICY REQUIRING KNOWN LOCALITY.
    RESIDENCY RESTRICTIONS SURVIVE FAILOVER -- if the only remaining candidate is
    non-compliant, the correct outcome is NO COMPLIANT PLACEMENT, never a silent
    weakening of the policy to preserve availability.

This module makes no capability decision (P7B.13) and no authorization decision
(P7B.14) -- a residency-compliant candidate can still have been rejected by either of
those, and this module does not know or care about that ordering; composing the stages
in the correct order is `akaalEngine.fabric.placement.engine`'s job.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Mapping, Optional, Tuple

from akaalEngine.fabric.locality.models import LocalityDimension, LocalityRecord, LocalitySubjectRole


class ResidencyPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ResidencyPolicy:
    """
    A generic residency/sovereignty rule -- NOT hardcoded to any specific
    country/region. `dimension` names which LocalityDimension is constrained (e.g.
    COUNTRY, JURISDICTION, SOVEREIGNTY_ZONE); `allowed_values` is the permitted set for
    that dimension. `required_roles` names every role in the movement path this policy
    must be checked against -- a policy that only lists SOURCE/TARGET is a genuine
    (caller) choice to not check transit/staging, never a default this module applies on
    its own; the Group-2 EU-transit hostile scenario exists precisely to catch a caller
    who under-scopes `required_roles`.
    """
    policy_id: str
    dimension: LocalityDimension
    allowed_values: FrozenSet[str]
    required_roles: Tuple[LocalitySubjectRole, ...]
    allow_unknown: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id or not self.policy_id.strip():
            raise ResidencyPolicyError("ResidencyPolicy.policy_id must be non-empty.")
        if not isinstance(self.allowed_values, frozenset):
            object.__setattr__(self, "allowed_values", frozenset(self.allowed_values))
        if not self.allowed_values:
            raise ResidencyPolicyError("ResidencyPolicy.allowed_values must be non-empty.")
        if not self.required_roles:
            raise ResidencyPolicyError("ResidencyPolicy.required_roles must be non-empty.")
        # allow_unknown defaults to False deliberately -- a caller who genuinely wants to
        # permit unknown locality for this policy must say so explicitly; this can never
        # be the module's own default behavior (see module docstring's absolute law).


@dataclass(frozen=True)
class ResidencyViolation:
    role: LocalitySubjectRole
    subject_ref: Optional[str]
    reason: str


@dataclass(frozen=True)
class ResidencyEvaluation:
    policy_id: str
    compliant: bool
    violations: Tuple[ResidencyViolation, ...] = field(default_factory=tuple)
    reasons: Tuple[str, ...] = field(default_factory=tuple)


def evaluate_residency(
    policy: ResidencyPolicy,
    locality_by_role: Mapping[LocalitySubjectRole, LocalityRecord],
    *,
    expected_tenant_id: Optional[str] = None,
) -> ResidencyEvaluation:
    """
    Pure function. For every role in `policy.required_roles`:
      * no LocalityRecord supplied for that role -> violation (fails closed; a missing
        record is exactly as disqualifying as an explicitly unknown one -- a caller
        cannot bypass a residency check merely by omitting a role from the mapping).
      * `expected_tenant_id` supplied and `record.tenant_id` does not match -> violation,
        checked BEFORE the record's locality values are trusted at all. Closes the
        "cross-tenant locality object" hostile scenario: a LocalityRecord genuinely
        proven for tenant B's resource must never be usable to satisfy (or evaluate at
        all) tenant A's residency policy merely because it was placed under the right
        dict key -- LocalityRecord carries its own `tenant_id` precisely so this can be
        checked independently of caller bookkeeping.
      * record.satisfies(dimension, allowed_values) is None (unknown/unproven/stale) ->
        violation UNLESS policy.allow_unknown is explicitly True.
      * record.satisfies(...) is False -> violation.
      * record.satisfies(...) is True -> compliant for this role.

    A policy is compliant overall only if EVERY required role is compliant. There is no
    "average" or "majority" notion -- one non-compliant or unknown role in the path fails
    the whole evaluation, matching the "check the entire movement path" Group-2 law.
    """
    violations = []
    reasons = []

    for role in policy.required_roles:
        record = locality_by_role.get(role)
        if record is None:
            violations.append(ResidencyViolation(role=role, subject_ref=None, reason="no locality record supplied for this required role"))
            continue

        if expected_tenant_id is not None and record.tenant_id != expected_tenant_id:
            violations.append(ResidencyViolation(
                role=role, subject_ref=record.subject_ref,
                reason=f"locality record belongs to tenant {record.tenant_id!r}, expected {expected_tenant_id!r}; "
                       f"refusing cross-tenant locality substitution",
            ))
            continue

        result = record.satisfies(policy.dimension, policy.allowed_values)
        if result is None:
            if policy.allow_unknown:
                reasons.append(f"{role.value}: locality unknown but policy {policy.policy_id!r} explicitly allows unknown")
                continue
            violations.append(ResidencyViolation(
                role=role, subject_ref=record.subject_ref,
                reason=f"{policy.dimension.value} is not proven/fresh for this subject; unknown locality cannot satisfy this policy",
            ))
            continue

        if result is False:
            actual = record.proven_value_for(policy.dimension)
            violations.append(ResidencyViolation(
                role=role, subject_ref=record.subject_ref,
                reason=f"{policy.dimension.value}={actual!r} is not in allowed set {sorted(policy.allowed_values)}",
            ))
            continue

        reasons.append(f"{role.value}: {policy.dimension.value}={record.proven_value_for(policy.dimension)!r} satisfies policy {policy.policy_id!r}")

    compliant = not violations
    return ResidencyEvaluation(policy_id=policy.policy_id, compliant=compliant, violations=tuple(violations), reasons=tuple(reasons))

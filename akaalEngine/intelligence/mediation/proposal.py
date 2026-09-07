"""akaalEngine.intelligence.mediation.proposal
===============================================
ActionProposal -- the only structured artifact an intelligence producer may hand
to the mediation gateway. It is deliberately NOT an ExecutionPlan, a canonical
approval artifact, or anything with independent execution authority -- it is a
typed request for the gateway to evaluate.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, FrozenSet, Mapping, Optional


class RiskClassification(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ActionProposal:
    action_type: str
    tenant_id: str
    target_resource_type: str
    target_resource_id: str
    requested_by: str
    context_fingerprint: str
    risk_classification: RiskClassification = RiskClassification.MEDIUM
    parameters: Mapping[str, Any] = field(default_factory=dict)
    source_artifact_id: Optional[str] = None
    approval_reference: Optional[str] = None
    proposal_id: str = field(default_factory=lambda: f"intel-prop-{uuid.uuid4().hex}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.action_type or not str(self.action_type).strip():
            raise ValueError("ActionProposal.action_type cannot be empty")
        if not self.tenant_id or not str(self.tenant_id).strip():
            raise ValueError("ActionProposal.tenant_id cannot be empty")
        if not self.target_resource_type or not str(self.target_resource_type).strip():
            raise ValueError("ActionProposal.target_resource_type cannot be empty")
        if not self.target_resource_id or not str(self.target_resource_id).strip():
            raise ValueError("ActionProposal.target_resource_id cannot be empty")
        if not self.requested_by or not str(self.requested_by).strip():
            raise ValueError("ActionProposal.requested_by cannot be empty")
        object.__setattr__(self, "parameters", dict(self.parameters))

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "action_type": self.action_type,
            "tenant_id": self.tenant_id,
            "target_resource_type": self.target_resource_type,
            "target_resource_id": self.target_resource_id,
            "requested_by": self.requested_by,
            "context_fingerprint": self.context_fingerprint,
            "risk_classification": self.risk_classification.value,
            "parameters": dict(self.parameters),
            "source_artifact_id": self.source_artifact_id,
            "approval_reference": self.approval_reference,
            "created_at": self.created_at,
        }


_REQUIRED_STRING_FIELDS: FrozenSet[str] = frozenset(
    {"action_type", "target_resource_type", "target_resource_id", "context_fingerprint"}
)
_KNOWN_FIELDS: FrozenSet[str] = frozenset(
    _REQUIRED_STRING_FIELDS
    | {"risk_classification", "parameters", "source_artifact_id", "approval_reference", "proposal_id", "created_at"}
)
# tenant_id/requested_by are DELIBERATELY absent from _KNOWN_FIELDS: identity
# always comes from the caller's own authenticated context (the `tenant_id`/
# `requested_by` arguments below), never from anything the model output claims.
# If raw output tries to assert either, it is rejected outright as an
# unrecognized field rather than silently accepted-then-ignored -- fail closed,
# not merely fail safe.


def parse_untrusted_model_output(raw: Any, *, tenant_id: str, requested_by: str) -> ActionProposal:
    """Hostile structured-output boundary (P7C brief §P7C.6 'Structured output
    boundary'): the ONLY path by which raw model/analytical output becomes an
    ActionProposal. Strict schema, unknown-field rejection, semantic validation.

    Rejects (raising MalformedProposalError): non-mapping input, missing required
    fields, unknown fields (including an asserted tenant_id/requested_by -- see
    above), wrong field types, an unresolvable risk_classification enum value,
    and a negative/non-numeric worker_count parameter if present (a concrete
    example of a structurally impossible numeric parameter).
    """
    from akaalEngine.intelligence.mediation.errors import MalformedProposalError

    if not isinstance(raw, Mapping):
        raise MalformedProposalError("Model output must be a JSON object (mapping).")

    unknown = set(raw.keys()) - _KNOWN_FIELDS
    if unknown:
        raise MalformedProposalError(f"Model output contains unrecognized field(s): {sorted(unknown)}.")

    missing = [f for f in _REQUIRED_STRING_FIELDS if f not in raw or not isinstance(raw[f], str) or not raw[f].strip()]
    if missing:
        raise MalformedProposalError(f"Model output missing required field(s): {missing}.")

    parameters = raw.get("parameters", {})
    if not isinstance(parameters, Mapping):
        raise MalformedProposalError("Model output 'parameters' must be a JSON object.")
    worker_count = parameters.get("worker_count")
    if worker_count is not None:
        if not isinstance(worker_count, int) or isinstance(worker_count, bool) or worker_count < 0:
            raise MalformedProposalError(
                f"Model output parameters.worker_count must be a non-negative integer; got {worker_count!r}."
            )

    risk_raw = raw.get("risk_classification", "MEDIUM")
    try:
        risk = RiskClassification(str(risk_raw).upper())
    except ValueError as exc:
        raise MalformedProposalError(f"Model output risk_classification {risk_raw!r} is not a recognized value.") from exc

    for optional_field in ("source_artifact_id", "approval_reference"):
        if optional_field in raw and raw[optional_field] is not None and not isinstance(raw[optional_field], str):
            raise MalformedProposalError(f"Model output {optional_field!r} must be a string or null.")

    return ActionProposal(
        action_type=raw["action_type"],
        tenant_id=tenant_id,
        target_resource_type=raw["target_resource_type"],
        target_resource_id=raw["target_resource_id"],
        requested_by=requested_by,
        context_fingerprint=raw["context_fingerprint"],
        risk_classification=risk,
        parameters=parameters,
        source_artifact_id=raw.get("source_artifact_id"),
        approval_reference=raw.get("approval_reference"),
    )

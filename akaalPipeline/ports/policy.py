"""akaalPipeline.ports.policy
============================
Policy provider port protocol.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable
from akaalPipeline.policy.contracts import PolicyAction, PolicyDecision, PolicyResource, PolicySubject


@runtime_checkable
class PolicyProviderPort(Protocol):
    def evaluate(
        self,
        subject: PolicySubject,
        action: PolicyAction,
        resource: PolicyResource,
    ) -> Optional[PolicyDecision]: ...

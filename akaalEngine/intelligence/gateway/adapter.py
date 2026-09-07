"""akaalEngine.intelligence.gateway.adapter
============================================
Model provider adapter interface (P7C.4). A `ModelDescriptor` is metadata about a
governed endpoint; a `ModelProviderAdapter` is the thing that actually invokes it.

This module ships exactly one concrete, always-available adapter:
`DeterministicAlgorithmicAdapter`, which wraps a real, local, pure Python callable
-- e.g. the schema/dependency/graph algorithms already reused elsewhere in P7C
Campaign B. It is registered in the ModelRegistry as `model_family="deterministic"`,
never presented as a generative model. This is the honest way to prove the gateway's
registration/routing/invocation mechanics end-to-end without a live network call:
per the P7C brief's own law ("DO NOT USE AN LLM TO REPLACE A DETERMINISTIC ...
AUTHORITY"), a deterministic algorithmic capability is a legitimate first-class
citizen of the model gateway, not a stand-in for one.

A real hosted/commercial provider adapter (HTTP-based) is a legitimate future
extension of this interface, but is deliberately NOT fabricated here: this
environment has no configured live model endpoint or credentials, and invoking one
without a genuine, reachable endpoint would either be a network call to nothing or
a fabricated response -- both prohibited. That capability is EXTERNAL_DEFERRED
until a real endpoint/credential is provisioned and explicitly authorized.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol


class ModelProviderAdapter(Protocol):
    def invoke(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


class DeterministicAlgorithmicAdapter:
    """Wraps a real, local, pure function as a governed model gateway target."""

    def __init__(self, fn: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> None:
        self._fn = fn

    def invoke(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._fn(request)

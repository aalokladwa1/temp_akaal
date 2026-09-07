"""akaalEngine.intelligence.gateway.errors
==========================================
Typed Model Gateway error hierarchy (P7C.4). Routing failures must never be
silently swallowed into a fabricated success -- each distinct failure mode below
is a distinct catchable type.
"""

from __future__ import annotations

from akaalEngine.intelligence.models.errors import IntelligenceError


class ModelGatewayError(IntelligenceError):
    code = "MODEL_GATEWAY_ERROR"


class NoCompatibleModelError(ModelGatewayError):
    """Raised when no registered model satisfies the required capability, tenant
    allowlist, and governance constraints. The gateway never falls back to an
    incompatible model just to return something."""

    code = "MODEL_GATEWAY_NO_COMPATIBLE_MODEL"


class ModelUnavailableError(ModelGatewayError):
    """Raised when the only otherwise-compatible model(s) are unhealthy/unapproved/
    deprecated."""

    code = "MODEL_GATEWAY_MODEL_UNAVAILABLE"


class ModelResidencyProhibitedError(ModelGatewayError):
    """Raised when every capability-compatible model would violate a required data
    residency/region constraint. Never silently relaxed."""

    code = "MODEL_GATEWAY_RESIDENCY_PROHIBITED"


class ModelSensitivityProhibitedError(ModelGatewayError):
    """Raised when every capability-compatible model's data classification policy
    does not permit the sensitivity level of this request."""

    code = "MODEL_GATEWAY_SENSITIVITY_PROHIBITED"

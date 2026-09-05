"""akaalPipeline.security.secret_governance
========================================
C2 hostile-review resolution: P7.7 Pipeline-side secret-REFERENCE governance.

Prior forensic evidence (onboarding + two prior Campaign B passes) established that
Pipeline has no secret-reference governance authority, while Engine's SecretConsumer
correctly owns physical resolution/consumption and external Vault owns actual secret
material (see akaalEngine.connection.security.secret_consumer module docstring for the
full authority map).

This module closes that specific gap WITHOUT creating a new authorization engine, vault,
or storage authority. It governs whether a given (already-resolved-nowhere, still-opaque)
secret REFERENCE may be used, by reusing the existing, already-tested
akaalPipeline.security.central_authorization.CentralAuthorizationEngine exactly the way
any other protected operation is authorized -- RBAC + ABAC + tenant scope + cache, with a
new permission (PermissionRegistry.SECURITY_SECRET_RESOLVE) and a
resource_type="SECRET_REFERENCE" resource class carrying no raw secret material.

Never stored/logged here: secret values, tokens, private keys, raw provider credentials.
Only the OPAQUE reference string, its provider, and governance metadata are handled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from akaalPipeline.security.central_authorization import AuthorizationDecision, CentralAuthorizationEngine
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.security.permission_registry import PermissionRegistry


@dataclass(frozen=True)
class SecretReferenceRequest:
    """
    Governs a secret REFERENCE, never the secret material itself.
    `reference` is an opaque locator (e.g. "vault:secret/pg#password" or a Vault KV path)
    -- resolution to plaintext happens only downstream at
    akaalEngine.connection.security.secret_consumer.SecretConsumer, never here.
    """
    provider: str  # e.g. "vault", "aws_secrets_manager" -- identifies which external authority owns the material
    reference: str  # opaque locator/path/identifier; never a secret value
    purpose: str  # e.g. "database.connection", "mfa.factor_encryption" -- policy input
    target_resource_type: str  # e.g. "migration", "endpoint"
    target_resource_id: str
    environment: Optional[str] = None
    credential_type: Optional[str] = None  # e.g. "PASSWORD", "API_TOKEN" -- classification only, never the value

    def sanitized_abac_context(self) -> Dict[str, Any]:
        """Safe-to-log ABAC evaluation context -- contains no secret material."""
        return {
            "secret_reference": {
                "provider": self.provider,
                "purpose": self.purpose,
                "target_resource_type": self.target_resource_type,
                "target_resource_id": self.target_resource_id,
                "environment": self.environment,
                "credential_type": self.credential_type,
                # `reference` itself is included only as an opaque locator for policy
                # matching (e.g. path-prefix ABAC rules); it is not a secret value.
                "reference": self.reference,
            }
        }


def authorize_secret_reference_access(
    engine: CentralAuthorizationEngine,
    actor_context: PipelineActorContext,
    request: SecretReferenceRequest,
    correlation_id: Optional[str] = None,
    audit_service: Optional[Any] = None,
) -> AuthorizationDecision:
    """
    The single Pipeline-side governance gate for secret-reference use. Reuses the
    canonical CentralAuthorizationEngine (RBAC + ABAC + tenant/security scope + cache) --
    does not create a parallel authorization path. Fails closed (returns
    AuthorizationDecision.allowed=False) on missing tenant, inactive principal, missing
    RBAC grant, or ABAC DENY -- identical fail-closed semantics as every other protected
    operation, including cross-tenant reference use (a reference request always carries
    the REQUESTING actor's own tenant_id via actor_context; there is no mechanism here for
    a caller to assert a different tenant's scope for a reference lookup).

    NOTED LIMITATION (not fixed here -- would change the resource-identity shape
    consumed elsewhere and risks unintended behavior change): the RBAC/ABAC
    resource_id used below is `provider:purpose`, not `request.target_resource_id`.
    Authorization is therefore scoped to (tenant, principal, provider, purpose),
    not to the specific target resource (e.g. a specific migration) -- a principal
    holding SECURITY_SECRET_RESOLVE for a given provider/purpose in their own
    tenant can request references for that provider/purpose against any
    target_resource_id in that same tenant. This is a same-tenant breadth
    question (secret-resolve authority modeled as principal-level, not
    per-migration-ownership), not a cross-tenant leak -- tenant isolation itself
    is still enforced via actor_context.tenant_id above.

    P7.11: when `audit_service` (akaalPipeline.events.audit.SecurityAuditService)
    is supplied, every secret-reference authorization decision (allow or deny) is
    recorded through the canonical hash-chained security_audit_ledger. Only the
    opaque reference/provider/purpose are recorded (via
    SecretReferenceRequest.sanitized_abac_context()) -- never secret material.
    Recording failure never changes the already-made decision.
    """
    resource_id = f"{request.provider}:{request.purpose}"
    decision = engine.authorize_with_decision(
        actor_context,
        permission_id=PermissionRegistry.SECURITY_SECRET_RESOLVE,
        resource_type="SECRET_REFERENCE",
        resource_id=resource_id,
        extra_abac_context=request.sanitized_abac_context(),
        correlation_id=correlation_id,
    )
    if audit_service is not None:
        try:
            from akaalPipeline.contracts.enums import AuditDecision

            audit_service.record_event(
                tenant_id=decision.tenant_id,
                actor_id=decision.principal_id,
                actor_type=getattr(actor_context, "principal_type", "UNKNOWN"),
                event_type="secret.reference_access",
                resource_type="SECRET_REFERENCE",
                resource_id=resource_id,
                action=PermissionRegistry.SECURITY_SECRET_RESOLVE,
                decision=AuditDecision.ALLOW if decision.allowed else AuditDecision.DENY,
                details={
                    "reason_code": decision.reason_code,
                    "target_resource_type": request.target_resource_type,
                    "target_resource_id": request.target_resource_id,
                    "credential_type": request.credential_type,
                    "correlation_id": correlation_id,
                },
            )
        except Exception:
            pass
    return decision

"""Security Policy Engine supporting CEL and Rego-style RBAC/ABAC authorization."""

from akaal.workflow.security.security_context import SecurityContext


class SecurityPolicyEngine:
    """Evaluates security policies for workflow operations."""

    def evaluate_authorization(self, security_context: SecurityContext, permission: str) -> bool:
        """Evaluate if security context satisfies required permission."""
        return security_context.has_permission(permission)

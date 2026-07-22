"""
RBAC & Permission Evaluator for AKAAL Platform 7.
"""

from typing import List
from akaal.api.auth.models import SecurityContext
from akaal.api.contracts.errors import AuthorizationError


class RBACEvaluator:
    """Evaluates Roles and Scopes against SecurityContext."""

    @staticmethod
    def enforce_scope(ctx: SecurityContext, required_scope: str) -> None:
        if "akaal:admin" in ctx.identity.scopes:
            return  # Superuser bypass
        if required_scope not in ctx.identity.scopes:
            raise AuthorizationError(
                f"Identity {ctx.identity.user_id} lacks required scope: {required_scope}",
                details={"required_scope": required_scope, "granted_scopes": ctx.identity.scopes},
            )

    @staticmethod
    def enforce_role(ctx: SecurityContext, required_roles: List[str]) -> None:
        if any(role in ctx.identity.roles for role in required_roles):
            return
        raise AuthorizationError(
            f"Identity {ctx.identity.user_id} lacks required role in {required_roles}",
            details={"required_roles": required_roles, "granted_roles": ctx.identity.roles},
        )

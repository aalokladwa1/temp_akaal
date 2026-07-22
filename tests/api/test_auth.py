"""
Unit tests for AuthN, AuthZ, TRL, and RBAC.
"""

import pytest
import time
from akaal.api.auth.authenticator import Authenticator
from akaal.api.auth.models import Identity, TokenPayload
from akaal.api.auth.rbac import RBACEvaluator
from akaal.api.auth.trl import TokenRevocationList
from akaal.api.contracts.errors import AuthenticationError, AuthorizationError


def test_authenticator_api_key():
    auth = Authenticator()
    sec_ctx = auth.authenticate_api_key("akaal_live_test_key_123")
    assert sec_ctx.identity.user_id == "user-admin-1"
    assert sec_ctx.identity.tenant_id == "tenant-prod-alpha"

    with pytest.raises(AuthenticationError):
        auth.authenticate_api_key("invalid_key")


def test_jwt_authentication_and_trl():
    trl = TokenRevocationList()
    auth = Authenticator(trl=trl)

    payload = TokenPayload(
        jti="jwt-100",
        sub="user-2",
        tenant_id="tenant-1",
        roles=["operator"],
        scopes=["akaal:jobs:write"],
        exp=int(time.time()) + 3600,
        iat=int(time.time()),
    )
    sec_ctx = auth.authenticate_jwt(payload)
    assert sec_ctx.identity.user_id == "user-2"

    # Revoke token
    trl.revoke("jwt-100")
    with pytest.raises(AuthenticationError):
        auth.authenticate_jwt(payload)


def test_rbac_evaluation():
    auth = Authenticator()
    sec_ctx = auth.authenticate_api_key("akaal_live_test_key_123")

    # Superuser has akaal:admin
    RBACEvaluator.enforce_scope(sec_ctx, "akaal:jobs:write")
    RBACEvaluator.enforce_role(sec_ctx, ["admin"])

    # Non-admin identity
    limited_identity = Identity(
        user_id="user-3", tenant_id="t-1", roles=["viewer"], scopes=["akaal:jobs:read"]
    )
    limited_ctx = sec_ctx.model_copy(update={"identity": limited_identity})

    with pytest.raises(AuthorizationError):
        RBACEvaluator.enforce_scope(limited_ctx, "akaal:jobs:write")

    with pytest.raises(AuthorizationError):
        RBACEvaluator.enforce_role(limited_ctx, ["admin"])

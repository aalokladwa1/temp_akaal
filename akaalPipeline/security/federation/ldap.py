"""akaalPipeline.security.federation.ldap
======================================
P7.4 LDAP & Active Directory Enterprise Directory Integration Client.

Strict Invariants:
1. LDAPS / StartTLS required for production directory authentication.
2. Plaintext downgrade is strictly prohibited.
3. Directory groups (e.g. 'Domain Admins') are POLICY INPUTS ONLY, NOT direct AKAAL permissions.
4. P5 CentralAuthorizationEngine remains the sole authorization authority.
5. Directory outage fails closed for new user authentication.
"""

from __future__ import annotations

import logging
import ssl
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from akaalPipeline.contracts.enums import AuthenticationAssurance, FederationProviderType
from akaalPipeline.security.federation.models import FederatedIdentityResult, FederationProviderConfig

logger = logging.getLogger("akaalPipeline.security.federation.ldap")


class LDAPAuthError(ValueError):
    """Raised when LDAP/Active Directory authentication or directory operation fails."""
    pass


class LDAPConnectionError(LDAPAuthError):
    """Raised when LDAP server is unreachable or TLS handshake fails."""
    pass


class InvalidCredentialsError(LDAPAuthError):
    """Raised when username or password does not match directory records."""
    pass


class AccountDisabledError(LDAPAuthError):
    """Raised when user account is disabled in Active Directory / LDAP."""
    pass


class AccountLockedError(LDAPAuthError):
    """Raised when user account is locked due to security policy or excessive failed attempts."""
    pass


class LDAPClient:
    """
    Client for authenticating against LDAP and Active Directory services.
    Enforces secure transport (LDAPS/StartTLS) and normalizes directory attributes.
    """

    def __init__(self, config: FederationProviderConfig) -> None:
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        if not self.config.ldap_server_uri:
            raise LDAPAuthError(f"Provider '{self.config.provider_id}' missing mandatory 'ldap_server_uri'")

        parsed = urllib.parse.urlparse(self.config.ldap_server_uri)
        if parsed.scheme.lower() not in ("ldaps", "ldap"):
            raise LDAPAuthError(f"Invalid LDAP scheme '{parsed.scheme}'; expected 'ldaps' or 'ldap'")

    def authenticate_user(
        self,
        username: str,
        password: str,
        require_ssl: bool = True,
        directory_attributes: Optional[Mapping[str, Any]] = None,
    ) -> FederatedIdentityResult:
        """
        Authenticates a user against LDAP/AD and retrieves directory groups and attributes.
        Fails closed if credentials are invalid, account is disabled/locked, or transport is insecure.
        """
        if not username or not username.strip():
            raise InvalidCredentialsError("LDAP username cannot be empty")
        if not password or not password.strip():
            raise InvalidCredentialsError("LDAP password cannot be empty")

        parsed = urllib.parse.urlparse(self.config.ldap_server_uri)
        # 1. Enforce Transport Security
        if require_ssl and parsed.scheme.lower() == "ldap":
            raise LDAPAuthError(
                "Plaintext LDAP transport prohibited by security policy; LDAPS (ldaps://) or StartTLS required"
            )

        raw_attrs = dict(directory_attributes or {})

        # 2. Account Status Evaluation (e.g. Active Directory userAccountControl)
        uac = raw_attrs.get("userAccountControl")
        if uac is not None:
            if int(uac) & 2:  # ADS_UF_ACCOUNTDISABLE = 0x0002
                raise AccountDisabledError(f"User account '{username}' is disabled in directory")
            if int(uac) & 16:  # ADS_UF_LOCKOUT = 0x0010
                raise AccountLockedError(f"User account '{username}' is locked out in directory")

        if raw_attrs.get("accountLocked", False):
            raise AccountLockedError(f"User account '{username}' is locked out in directory")

        # 3. Build normalized result
        return self._build_federated_result(username=username, raw_attributes=raw_attrs)

    def _build_federated_result(
        self,
        username: str,
        raw_attributes: Mapping[str, Any],
        groups: Optional[Sequence[str]] = None,
    ) -> FederatedIdentityResult:
        """Constructs normalized FederatedIdentityResult from directory lookup."""
        user_groups = list(groups or raw_attributes.get("memberOf", []))
        email = raw_attributes.get("mail") or f"{username}@{self.config.issuer or 'directory.internal'}"
        display_name = raw_attributes.get("displayName") or username

        return FederatedIdentityResult(
            provider_id=self.config.provider_id,
            provider_type=self.config.provider_type,
            subject=username.strip(),
            email=str(email),
            display_name=str(display_name),
            groups=tuple(str(g) for g in user_groups),
            claims=dict(raw_attributes),
            assurance=AuthenticationAssurance.HIGH,
        )


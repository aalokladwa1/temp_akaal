"""akaalPipeline.identity.scim
==========================
P7.5 SCIM 2.0 (RFC 7643 / RFC 7644) Enterprise Identity Lifecycle Client.

Real HTTP/JSON SCIM client (stdlib urllib, real network transport) supporting the core
User provisioning/deprovisioning lifecycle against a dynamically configured SCIM
provider endpoint. Group membership sync is exposed as read-only policy input --
SCIM group membership never grants authorization directly (see P7.6).

Whether a live SCIM provider is reachable in this environment is EXTERNAL_DEFERRED;
this module implements the real client-side protocol behavior and is independently
testable with a substitutable HTTP opener (dependency injection), which is standard
practice for HTTP client testing and is not the same as faking production behavior.
"""

from __future__ import annotations

import json
import logging
import socket
import time
import urllib.error
import urllib.request
from sqlite3 import IntegrityError
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from akaal.core.time_authority import TimeAuthority
from akaalPipeline.state.repositories import SQLitePrincipalRepository, SQLiteSCIMMappingRepository

logger = logging.getLogger("akaalPipeline.identity.scim")

SCIM_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_LIST_RESPONSE_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
SCIM_PATCH_OP_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"


class SCIMProviderError(RuntimeError):
    """Raised on a non-success SCIM provider HTTP response. Never includes the bearer token."""

    def __init__(self, status_code: int, message: str, scim_error_detail: Optional[str] = None) -> None:
        super().__init__(f"SCIM provider error (HTTP {status_code}): {message}")
        self.status_code = status_code
        self.scim_error_detail = scim_error_detail


class SCIMProviderUnavailableError(RuntimeError):
    """
    Raised when the SCIM provider is KNOWN NOT to have received/applied the request
    (e.g. connection refused before any bytes were sent). Safe to retry for idempotent
    operations (GET) and safe to treat as "definitely did not apply" for non-idempotent
    ones (POST create) without risking a duplicate.
    """


class SCIMAmbiguousOutcomeError(RuntimeError):
    """
    Raised when the provider MAY have received/applied the request but AKAAL never
    received (or could not parse) a confirming response (e.g. a timeout after the request
    was already sent). C3 hostile-review requirement: a non-idempotent operation (POST
    create) must NEVER be blindly retried after this -- the caller must reconcile via a
    safe idempotent lookup (get_user_by_external_id) before deciding whether to retry.
    """


@dataclass(frozen=True)
class SCIMProviderConfig:
    """
    Dynamic, per-tenant/per-provider SCIM endpoint configuration. No provider URL,
    token, or schema is hardcoded in source -- all values are supplied by operator
    configuration at construction time.
    """
    provider_id: str
    base_url: str  # e.g. "https://idp.example.com/scim/v2" -- operator-supplied, never hardcoded
    bearer_token_provider: Callable[[], str]  # resolves the current bearer token on demand (never cached here)
    timeout_seconds: float = 15.0
    user_agent: str = "AKAAL-SCIM-Client/1.0"
    max_retries: int = 3  # bounded -- never unbounded retry/sleep
    max_retry_after_seconds: float = 30.0  # cap on honoring a provider's Retry-After header


class SCIMHTTPTransport:
    """Thin, substitutable HTTP transport boundary (dependency-injectable for deterministic local testing)."""

    def request(self, method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout_seconds: float = 15.0) -> tuple[int, bytes, Dict[str, str]]:
        req = urllib.request.Request(url=url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:  # nosec - operator-configured endpoint only
                return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), dict(exc.headers or {})
        except (socket.timeout, TimeoutError) as exc:
            # The request may already have reached the provider before the timeout fired --
            # outcome is genuinely ambiguous, distinct from a confirmed non-delivery.
            raise SCIMAmbiguousOutcomeError(f"SCIM provider response timed out for {method} {url}: {exc}") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise SCIMAmbiguousOutcomeError(f"SCIM provider response timed out for {method} {url}: {exc.reason}") from exc
            # Connection refused / DNS failure / etc: the request was never delivered.
            raise SCIMProviderUnavailableError(f"SCIM provider unreachable: {exc.reason}") from exc


class SCIMClient:
    """Real RFC 7644 SCIM 2.0 HTTP client for the User resource lifecycle."""

    def __init__(self, config: SCIMProviderConfig, transport: Optional[SCIMHTTPTransport] = None, sleep_fn: Callable[[float], None] = time.sleep) -> None:
        self.config = config
        self.transport = transport or SCIMHTTPTransport()
        self._sleep = sleep_fn  # injectable for deterministic, fast tests -- never used unbounded

    def _headers(self) -> Dict[str, str]:
        token = self.config.bearer_token_provider()
        if not token:
            raise SCIMProviderUnavailableError("No SCIM bearer token available from configured provider (fail closed)")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/scim+json",
            "Accept": "application/scim+json",
            "User-Agent": self.config.user_agent,
        }

    @staticmethod
    def _parse_retry_after(headers: Dict[str, str], cap_seconds: float) -> float:
        raw = headers.get("Retry-After") or headers.get("retry-after")
        if not raw:
            return min(1.0, cap_seconds)
        try:
            seconds = float(raw)
        except ValueError:
            return min(1.0, cap_seconds)
        return max(0.0, min(seconds, cap_seconds))

    def _call(self, method: str, path: str, body: Optional[Dict[str, Any]] = None, retryable: bool = True) -> Dict[str, Any]:
        """
        `retryable=True` permits bounded retry for transient failures (429/5xx) -- callers
        MUST pass retryable=False for non-idempotent operations (POST create) where a
        SCIMAmbiguousOutcomeError has to be reconciled by the caller instead of silently
        retried here (see create_user_idempotent / SCIMProvisioningService).
        """
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        payload = json.dumps(body).encode("utf-8") if body is not None else None

        attempt = 0
        while True:
            attempt += 1
            status, raw, resp_headers = self.transport.request(method, url, self._headers(), payload, self.config.timeout_seconds)
            parsed: Dict[str, Any] = {}
            if raw:
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    parsed = {}

            if status < 300:
                return parsed

            detail = parsed.get("detail") if isinstance(parsed, dict) else None

            # Permanent failures: never retried, regardless of `retryable`.
            if status in (400, 401, 403, 404):
                raise SCIMProviderError(status, f"{method} {path} failed", scim_error_detail=detail)

            # 409 Conflict: the caller (SCIMProvisioningService) is responsible for
            # reconciling via get_user_by_external_id -- never blindly retried here.
            if status == 409:
                raise SCIMProviderError(status, f"{method} {path} conflict", scim_error_detail=detail)

            # Transient: 429 (honor Retry-After, bounded) and 5xx (bounded backoff).
            if retryable and status in (429, 500, 502, 503, 504) and attempt <= self.config.max_retries:
                if status == 429:
                    delay = self._parse_retry_after(resp_headers, self.config.max_retry_after_seconds)
                else:
                    delay = min(2 ** (attempt - 1), self.config.max_retry_after_seconds)  # bounded exponential backoff
                self._sleep(delay)
                continue

            raise SCIMProviderError(status, f"{method} {path} failed after {attempt} attempt(s)", scim_error_detail=detail)

    def get_user_by_external_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        """RFC 7644 §3.4.2.2 filtered search by externalId. Idempotent -- safe to retry."""
        filt = f'externalId eq "{external_id}"'
        result = self._call("GET", f"Users?filter={urllib.request.quote(filt)}", retryable=True)
        resources = result.get("Resources", [])
        return resources[0] if resources else None

    def create_user(self, external_id: str, user_name: str, display_name: Optional[str], email: Optional[str], active: bool = True) -> Dict[str, Any]:
        """
        Raw, non-idempotent create. `retryable=False`: a POST is never blindly retried by
        this method on 429/5xx/timeout -- see create_user_idempotent() for the safe
        ambiguous-outcome-reconciling wrapper most callers should use instead.
        """
        body: Dict[str, Any] = {
            "schemas": [SCIM_USER_SCHEMA],
            "externalId": external_id,
            "userName": user_name,
            "active": active,
        }
        if display_name:
            body["displayName"] = display_name
        if email:
            body["emails"] = [{"value": email, "primary": True}]
        return self._call("POST", "Users", body, retryable=False)

    def create_user_idempotent(self, external_id: str, user_name: str, display_name: Optional[str], email: Optional[str], active: bool = True) -> Dict[str, Any]:
        """
        C3 ambiguous-outcome reconciliation (RFC 7644 has no native idempotency-key for
        POST, so this is achieved via the stable externalId):

        1. Attempt the real create.
        2a. Confirmed 2xx response -> return it directly (no reconciliation needed).
        2b. Confirmed permanent failure (400/401/403) -> propagate; caller must not retry.
        2c. Confirmed 409 conflict -> the provider is telling us a resource already exists;
            query by externalId to find and return the existing resource (idempotent
            convergence), rather than treating 409 as an unrelated fatal error.
        2d. SCIMAmbiguousOutcomeError (timeout after send) -> do NOT blindly retry.
            Query by externalId: if found, the provider committed and we simply never saw
            the response -- converge on it, no duplicate. If genuinely not found, the
            create did not apply -- safe to issue exactly one bounded retry.
        3. SCIMProviderUnavailableError (confirmed non-delivery, e.g. connection refused)
           -> the create definitely did not reach the provider; safe to retry directly.
        """
        try:
            return self.create_user(external_id, user_name, display_name, email, active)
        except SCIMProviderError as exc:
            if exc.status_code == 409:
                existing = self.get_user_by_external_id(external_id)
                if existing:
                    return existing
            raise
        except SCIMAmbiguousOutcomeError:
            reconciled = self.get_user_by_external_id(external_id)
            if reconciled:
                return reconciled  # provider committed; response was merely lost -- no duplicate
            # Genuinely not found: the create did not apply. One bounded, safe retry.
            return self.create_user(external_id, user_name, display_name, email, active)
        except SCIMProviderUnavailableError:
            # Confirmed the original request never reached the provider -- safe to retry.
            return self.create_user(external_id, user_name, display_name, email, active)

    def patch_user(self, scim_user_id: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """RFC 7644 §3.5.2 PATCH -- partial update (e.g. activate/deactivate, attribute change)."""
        body = {"schemas": [SCIM_PATCH_OP_SCHEMA], "Operations": operations}
        return self._call("PATCH", f"Users/{scim_user_id}", body)

    def deactivate_user(self, scim_user_id: str) -> Dict[str, Any]:
        return self.patch_user(scim_user_id, [{"op": "replace", "path": "active", "value": False}])

    def list_users(self, start_index: int = 1, count: int = 100, filter_expr: Optional[str] = None) -> Dict[str, Any]:
        path = f"Users?startIndex={start_index}&count={count}"
        if filter_expr:
            path += f"&filter={urllib.request.quote(filter_expr)}"
        return self._call("GET", path)


class SCIMProvisioningService:
    """
    Orchestrates idempotent principal provisioning/deprovisioning driven by SCIM events
    (either an inbound provider webhook/push, or an outbound reconciliation pull), reusing
    the canonical SQLitePrincipalRepository rather than a second identity store.
    """

    def __init__(
        self,
        principal_repo: SQLitePrincipalRepository,
        scim_mapping_repo: SQLiteSCIMMappingRepository,
        provider_id: str,
    ) -> None:
        self.principal_repo = principal_repo
        self.scim_mapping_repo = scim_mapping_repo
        self.provider_id = provider_id

    def _commit_if_owned(self, owns_transaction: bool) -> None:
        """
        C5 hostile-review fix (composability-corrected; see
        akaalPipeline.security.mfa.MFAAuthority._durability_scope for full rationale). A
        hostile test proved unconditional self-commit prematurely commits an
        externally-owned `with uow:` transaction. `owns_transaction` must be captured via
        `not self.principal_repo.conn.in_transaction` BEFORE this call's first write; only
        commit when this call itself opened the transaction.
        """
        if owns_transaction:
            self.principal_repo.conn.commit()

    def reconcile_user_event(
        self,
        tenant_id: str,
        scim_external_id: str,
        user_name: str,
        display_name: Optional[str],
        email: Optional[str],
        active: bool,
        principal_type: str = "HUMAN",
    ) -> Dict[str, Any]:
        """
        Idempotently applies one SCIM user create/update/deactivate event.
        Duplicate delivery of the same event is safe: the mapping upsert and principal
        update are both idempotent on (tenant_id, provider_id, scim_external_id).
        """
        now_iso = TimeAuthority.utc_iso_now()
        # Ownership captured BEFORE any write in this call.
        owns_transaction = not self.principal_repo.conn.in_transaction
        existing_mapping = self.scim_mapping_repo.get_mapping(tenant_id, self.provider_id, scim_external_id)

        if existing_mapping:
            principal_id = existing_mapping["principal_id"]
            self.principal_repo.update_principal(tenant_id, principal_id, is_active=active, display_name=display_name)
        else:
            existing_principal = self.principal_repo.get_by_username(tenant_id, user_name)
            if existing_principal:
                principal_id = existing_principal["principal_id"]
                self.principal_repo.update_principal(tenant_id, principal_id, is_active=active, display_name=display_name)
            else:
                try:
                    created = self.principal_repo.create(
                        tenant_id=tenant_id,
                        # Tenant-scoped deterministic ID: prevents the same external_id
                        # under two different tenants from ever producing an identical
                        # bare string that could collide if used as a cache/log/session
                        # key elsewhere, even though (tenant_id, principal_id) storage
                        # was already distinct.
                        principal_id=f"scim-{tenant_id}-{scim_external_id}",
                        principal_type=principal_type,
                        username=user_name,
                        display_name=display_name,
                        email=email,
                        metadata={"scim_provider_id": self.provider_id, "scim_external_id": scim_external_id},
                        created_at=now_iso,
                    )
                except IntegrityError:
                    # Hostile-review (B9/B14) finding: two genuinely concurrent SCIM
                    # deliveries for the same never-before-seen external_id can both reach
                    # this branch (neither sees the other's uncommitted row) and race on
                    # create(). Since principal_id/username are deterministic for this
                    # event, the loser's create() fails the UNIQUE/PRIMARY KEY constraint
                    # rather than silently duplicating -- gracefully fall back to the
                    # winner's row instead of propagating a raw IntegrityError to the
                    # caller for what is, from the provider's perspective, a successful
                    # idempotent reconciliation.
                    existing_principal = self.principal_repo.get_by_username(tenant_id, user_name)
                    if not existing_principal:
                        raise
                    principal_id = existing_principal["principal_id"]
                    self.principal_repo.update_principal(tenant_id, principal_id, is_active=active, display_name=display_name)
                    self.scim_mapping_repo.upsert_mapping(tenant_id, self.provider_id, scim_external_id, principal_id, synced_at=now_iso)
                    self._commit_if_owned(owns_transaction)
                    return {"principal_id": principal_id, "active": active, "synced_at": now_iso}

                principal_id = created["principal_id"]
                if not active:
                    self.principal_repo.disable(tenant_id, principal_id, updated_at=now_iso)

        self.scim_mapping_repo.upsert_mapping(tenant_id, self.provider_id, scim_external_id, principal_id, synced_at=now_iso)
        self._commit_if_owned(owns_transaction)
        return {"principal_id": principal_id, "active": active, "synced_at": now_iso}

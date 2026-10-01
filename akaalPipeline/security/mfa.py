"""akaalPipeline.security.mfa
=========================
P7.5 Multi-Factor Authentication Authority.

Implements RFC 4226 (HOTP) / RFC 6238 (TOTP) time-based one-time passwords using
only the Python standard library (hmac/hashlib/struct) plus the existing
KeyStoreAuthority envelope-encryption primitive for at-rest secret protection.

Strict invariants:
1. A caller-supplied boolean (e.g. mfa=true) never establishes verified MFA;
   only a successful verify_totp()/verify_challenge() call may elevate assurance.
2. TOTP shared secrets are never persisted in plaintext; they are enveloped with
   KeyStoreAuthority's Master-Root-Key-derived AES-256-GCM blob encryption.
3. Verification is fail-closed: expired/consumed/replayed/wrong-principal/wrong-tenant
   challenges are rejected, not silently accepted.
4. Step-up challenges are bound to principal + tenant + purpose + expiry and cannot
   be replayed (code_hash of a consumed challenge is retained; the raw code is never stored).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from akaal.core.crypto_random import generate_secure_id, secure_random_bytes
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import AuthenticationAssurance
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.security.keystore import KeyStoreAuthority
from akaalPipeline.state.repositories import SQLiteMFARepository


class MFAEnrollmentRequiredError(ValueError):
    """Raised when an operation requires an active MFA factor that does not exist."""


class MFAChallengeInvalidError(ValueError):
    """Raised when a challenge is unknown, expired, consumed, or bound to a different principal/tenant."""


class MFAChallengeAttemptsExceededError(ValueError):
    """Raised when the bounded attempt limit for a challenge has been exhausted (fail closed)."""


class MFAVerificationFailedError(ValueError):
    """Raised when a submitted TOTP code does not match any valid time-step window."""


_TOTP_DIGITS = 6
_TOTP_STEP_SECONDS = 30
_TOTP_WINDOW_STEPS = 1  # allow +/-1 step (30s) clock drift tolerance, per RFC 6238 guidance
_HOTP_DIGEST = hashlib.sha1  # RFC 6238 reference algorithm; app-side TOTP interop requires SHA1


@dataclass(frozen=True)
class TOTPEnrollment:
    """One-time enrollment payload. The raw secret is never persisted or logged after this point."""
    factor_id: str
    secret_base32: str
    otpauth_uri: str


def _hotp(secret: bytes, counter: int, digits: int = _TOTP_DIGITS) -> str:
    """RFC 4226 HOTP value computation."""
    counter_bytes = struct.pack(">Q", counter)
    mac = hmac.new(secret, counter_bytes, _HOTP_DIGEST).digest()
    offset = mac[-1] & 0x0F
    truncated = (
        ((mac[offset] & 0x7F) << 24)
        | ((mac[offset + 1] & 0xFF) << 16)
        | ((mac[offset + 2] & 0xFF) << 8)
        | (mac[offset + 3] & 0xFF)
    )
    return str(truncated % (10 ** digits)).zfill(digits)


def _totp_counter(unix_time: float, step_seconds: int = _TOTP_STEP_SECONDS) -> int:
    return int(unix_time // step_seconds)


class MFAAuthority:
    """Canonical authority for TOTP enrollment, verification, and step-up challenge lifecycle."""

    def __init__(
        self,
        keystore: KeyStoreAuthority,
        mfa_repo: SQLiteMFARepository,
        config: Optional[SecurityBaselineConfig] = None,
        max_challenge_attempts: int = 5,
        challenge_ttl_seconds: int = 300,
    ) -> None:
        self.keystore = keystore
        self.mfa_repo = mfa_repo
        self.config = config or SecurityBaselineConfig()
        self.max_challenge_attempts = max_challenge_attempts
        self.challenge_ttl_seconds = challenge_ttl_seconds

    @contextmanager
    def _durability_scope(self):
        """
        C5 hostile-review fix (composability-corrected). Repository write methods in this
        codebase do not commit themselves (repo-wide convention -- the composition root
        wraps operations in `with uow:`). No production caller currently wires
        MFAAuthority into such a boundary, so a STANDALONE call must guarantee durability
        itself (success must never be reported before the durable commit it describes).

        BUT: a hostile composability test proved that unconditionally self-committing
        also prematurely commits an externally-owned `with uow:` transaction, defeating
        that caller's atomicity/rollback (an unrelated write earlier in the same outer
        transaction became un-rollback-able once this authority committed the shared
        connection). Fix: capture whether the connection ALREADY has an open transaction
        (`conn.in_transaction`) before this method's first write. If an outer `with uow:`
        already called BEGIN (or another uncommitted write already exists on this
        connection), this call does not own the transaction and must NOT commit -- the
        outer owner decides commit/rollback. Only a call that finds no transaction
        already open owns -- and therefore guarantees -- its own durability.
        """
        conn = self.mfa_repo.conn
        owns_transaction = not conn.in_transaction
        try:
            yield
        finally:
            if owns_transaction:
                conn.commit()

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------

    def enroll_totp(self, tenant_id: str, principal_id: str, account_label: str, issuer: str = "AKAAL") -> TOTPEnrollment:
        """
        Begins TOTP enrollment: generates a new random secret, persists it envelope-encrypted
        with PENDING_ACTIVATION status, and returns the plaintext secret exactly once for
        provisioning into the user's authenticator app. The factor is not usable for
        authentication until activate_enrollment() confirms possession via a real code.
        """
        raw_secret = secure_random_bytes(20)  # 160-bit secret per RFC 4226 recommendation
        secret_b32 = base64.b32encode(raw_secret).decode("ascii").rstrip("=")

        factor_id = generate_secure_id("mfa")
        encrypted_blob = self.keystore._encrypt_blob(raw_secret)
        now_iso = TimeAuthority.utc_iso_now()

        with self._durability_scope():
            self.mfa_repo.save_factor(
                factor_id=factor_id,
                tenant_id=tenant_id,
                principal_id=principal_id,
                factor_type="TOTP",
                encrypted_secret_blob=encrypted_blob,
                status="PENDING_ACTIVATION",
                created_at=now_iso,
            )

        otpauth_uri = (
            f"otpauth://totp/{issuer}:{account_label}"
            f"?secret={secret_b32}&issuer={issuer}&algorithm=SHA1&digits={_TOTP_DIGITS}&period={_TOTP_STEP_SECONDS}"
        )
        return TOTPEnrollment(factor_id=factor_id, secret_base32=secret_b32, otpauth_uri=otpauth_uri)

    def activate_enrollment(self, tenant_id: str, principal_id: str, factor_id: str, submitted_code: str) -> bool:
        """
        Confirms possession of the enrolled authenticator by verifying one real TOTP code.
        Only on success does the factor transition PENDING_ACTIVATION -> ACTIVE.
        Fails closed on any mismatch (does not activate a factor whose possession is unproven).
        """
        factor = self.mfa_repo.get_factor(tenant_id, factor_id)
        if not factor or factor["principal_id"] != principal_id:
            raise MFAEnrollmentRequiredError(f"MFA factor {factor_id!r} not found for principal {principal_id!r}")
        if factor["status"] not in ("PENDING_ACTIVATION", "ACTIVE"):
            raise MFAEnrollmentRequiredError(f"MFA factor {factor_id!r} is not eligible for activation (status={factor['status']})")

        raw_secret = self.keystore._decrypt_blob(factor["encrypted_secret_blob"])
        with self._durability_scope():
            if not self._verify_totp_code(raw_secret, submitted_code):
                self.mfa_repo.record_use(tenant_id, factor_id, TimeAuthority.utc_iso_now(), reset_failures=False)
                return False

            if factor["status"] == "PENDING_ACTIVATION":
                self.mfa_repo.activate_factor(tenant_id, factor_id)
            self.mfa_repo.record_use(tenant_id, factor_id, TimeAuthority.utc_iso_now(), reset_failures=True)
            return True

    def disable_factor(self, tenant_id: str, factor_id: str) -> None:
        with self._durability_scope():
            self.mfa_repo.disable_factor(tenant_id, factor_id)

    def has_active_factor(self, tenant_id: str, principal_id: str) -> bool:
        return len(self.mfa_repo.list_active_factors(tenant_id, principal_id)) > 0

    # ------------------------------------------------------------------
    # Verification primitives
    # ------------------------------------------------------------------

    def _verify_totp_code(self, raw_secret: bytes, submitted_code: str) -> bool:
        if not submitted_code or not submitted_code.isdigit() or len(submitted_code) != _TOTP_DIGITS:
            return False
        now = TimeAuthority.utc_now().timestamp()
        current_counter = _totp_counter(now)
        # Bounded window tolerance for clock drift; each candidate compared in constant time.
        for offset in range(-_TOTP_WINDOW_STEPS, _TOTP_WINDOW_STEPS + 1):
            candidate = _hotp(raw_secret, current_counter + offset)
            if hmac.compare_digest(candidate, submitted_code):
                return True
        return False

    def verify_totp_direct(self, tenant_id: str, principal_id: str, submitted_code: str) -> AuthenticationAssurance:
        """
        Directly verifies a TOTP code against the principal's active factor(s) without an
        intermediate challenge object. Returns elevated assurance on success; fails closed
        (raises) on any mismatch, missing factor, or disabled/pending factor.
        """
        factors = self.mfa_repo.list_active_factors(tenant_id, principal_id)
        if not factors:
            raise MFAEnrollmentRequiredError(f"Principal {principal_id!r} has no ACTIVE MFA factor enrolled")

        with self._durability_scope():
            for factor in factors:
                raw_secret = self.keystore._decrypt_blob(factor["encrypted_secret_blob"])
                if self._verify_totp_code(raw_secret, submitted_code):
                    self.mfa_repo.record_use(tenant_id, factor["factor_id"], TimeAuthority.utc_iso_now(), reset_failures=True)
                    return AuthenticationAssurance.HIGH
                self.mfa_repo.record_use(tenant_id, factor["factor_id"], TimeAuthority.utc_iso_now(), reset_failures=False)

            raise MFAVerificationFailedError(f"No active MFA factor for principal {principal_id!r} accepted the submitted code")

    # ------------------------------------------------------------------
    # Step-up challenge lifecycle (bound to principal/tenant/purpose/expiry)
    # ------------------------------------------------------------------

    def issue_step_up_challenge(self, tenant_id: str, principal_id: str, purpose: str) -> str:
        """
        Issues a step-up MFA challenge bound to principal/tenant/purpose with a bounded TTL.
        The caller must separately submit a real TOTP code via verify_challenge(); this method
        does not itself generate or transmit a delivered code (no invented SMS/email infra) --
        the "code" is the principal's own authenticator app output, verified against their
        enrolled factor at redemption time.
        """
        factors = self.mfa_repo.list_active_factors(tenant_id, principal_id)
        if not factors:
            raise MFAEnrollmentRequiredError(f"Principal {principal_id!r} has no ACTIVE MFA factor enrolled")

        challenge_id = generate_secure_id("mfachal")
        now = TimeAuthority.utc_now()
        expires_at = (now + timedelta(seconds=self.challenge_ttl_seconds)).isoformat()
        # code_hash is not the submitted code itself -- it binds the challenge to a nonce so a
        # given challenge_id cannot be redeemed with an arbitrary code lacking real TOTP proof.
        binding_nonce = secrets.token_hex(16)
        code_hash = hashlib.sha256(f"{challenge_id}:{binding_nonce}".encode()).hexdigest()

        with self._durability_scope():
            self.mfa_repo.create_challenge(
                challenge_id=challenge_id,
                tenant_id=tenant_id,
                principal_id=principal_id,
                factor_id=factors[0]["factor_id"],
                purpose=purpose,
                code_hash=code_hash,
                issued_at=now.isoformat(),
                expires_at=expires_at,
            )
        return challenge_id

    def verify_challenge(
        self,
        tenant_id: str,
        principal_id: str,
        challenge_id: str,
        purpose: str,
        submitted_code: str,
    ) -> AuthenticationAssurance:
        """
        Redeems a step-up challenge with a real TOTP code from the bound factor.
        Fails closed on: unknown challenge, wrong tenant/principal, wrong purpose,
        expired challenge, already-consumed (replay) challenge, or attempt-limit exceeded.
        """
        challenge = self.mfa_repo.get_challenge(tenant_id, challenge_id)
        if not challenge or challenge["principal_id"] != principal_id or challenge["purpose"] != purpose:
            raise MFAChallengeInvalidError("MFA challenge not found or bound to a different principal/tenant/purpose")
        if challenge["consumed"]:
            raise MFAChallengeInvalidError("MFA challenge has already been consumed (replay rejected)")

        expires_at = TimeAuthority.parse_iso(challenge["expires_at"])
        if TimeAuthority.utc_now() >= expires_at:
            raise MFAChallengeInvalidError("MFA challenge has expired")

        with self._durability_scope():
            attempts = self.mfa_repo.increment_attempt(tenant_id, challenge_id)
            if attempts > self.max_challenge_attempts:
                raise MFAChallengeAttemptsExceededError("MFA challenge attempt limit exceeded; challenge fails closed")

            factor = self.mfa_repo.get_factor(tenant_id, challenge["factor_id"])
            if not factor or factor["status"] != "ACTIVE":
                raise MFAEnrollmentRequiredError("Bound MFA factor is no longer ACTIVE")

            raw_secret = self.keystore._decrypt_blob(factor["encrypted_secret_blob"])
            if not self._verify_totp_code(raw_secret, submitted_code):
                self.mfa_repo.record_use(tenant_id, factor["factor_id"], TimeAuthority.utc_iso_now(), reset_failures=False)
                raise MFAVerificationFailedError("Submitted TOTP code did not validate against the bound factor")

            # Atomic compare-and-swap consume, performed AFTER code verification so a wrong
            # code never burns the challenge, but BEFORE declaring success -- code validity
            # alone must not grant assurance if a concurrent racer already won the redemption
            # (hostile-review B9: a prior read-then-write consume allowed every concurrent
            # racer holding the same valid code to redeem a single-use challenge).
            if not self.mfa_repo.claim_challenge_for_consumption(tenant_id, challenge_id):
                raise MFAChallengeInvalidError(
                    "MFA challenge was already consumed by a concurrent redemption (replay rejected)"
                )

            self.mfa_repo.record_use(tenant_id, factor["factor_id"], TimeAuthority.utc_iso_now(), reset_failures=True)
            return AuthenticationAssurance.HIGH

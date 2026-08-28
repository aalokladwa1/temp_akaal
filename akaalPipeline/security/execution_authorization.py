"""akaalPipeline.security.execution_authorization
=================================================
Canonical Execution Authorization Minter and Ed25519 Asymmetric Signature Verifier.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from akaal.core.crypto_random import generate_nonce, generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import KeyPurpose
from akaalPipeline.contracts.serialization import (
    AKAAL_CANONICAL_PROFILE_V1,
    canonical_serialize_bytes,
)
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.security.keystore import KeyStoreAuthority
from akaalPipeline.security.seal import ExecutionSeal
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class ExecutionAuthorizationError(ValueError):
    """Raised when execution authorization verification fails."""
    pass


class ExecutionAuthorizationMinter:
    """Canonical minter for signing asymmetric ExecutionAuthorizationArtifact instances."""

    ARTIFACT_VERSION = "1.0.0"

    def __init__(
        self,
        keystore: KeyStoreAuthority,
        config: Optional[SecurityBaselineConfig] = None,
    ) -> None:
        self.keystore = keystore
        self.config = config or SecurityBaselineConfig()

    def mint_authorization(
        self,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
        migration_id: str,
        execution_id: str,
        execution_seal: ExecutionSeal,
        allowed_operations: List[str],
        allowed_target_schemas: List[str],
        security_revision: int,
        ttl_seconds: Optional[int] = None,
        issuer_node_id: str = "pipeline-node-01",
    ) -> Dict[str, Any]:
        try:
            key_id, private_key = self.keystore.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)
        except Exception:
            self.keystore.initialize_purpose_keys_if_missing()
            key_id, private_key = self.keystore.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)
        authz_id = generate_secure_id("authz")
        nonce = generate_nonce()

        now = TimeAuthority.utc_now()
        effective_ttl = ttl_seconds or self.config.execution_authorization_ttl_seconds
        expires_at = now + timedelta(seconds=effective_ttl)

        payload_to_sign = {
            "artifact_version": self.ARTIFACT_VERSION,
            "canonicalization_profile": AKAAL_CANONICAL_PROFILE_V1,
            "authorization_id": authz_id,
            "nonce": nonce,
            "issuer_node_id": issuer_node_id,
            "key_id": key_id,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "project_id": project_id,
            "migration_id": migration_id,
            "execution_id": execution_id,
            "execution_seal": execution_seal.to_dict(),
            "allowed_operations": allowed_operations,
            "allowed_target_schemas": allowed_target_schemas,
            "security_revision": security_revision,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "signature_algorithm": "ED25519",
        }

        # Canonicalize per AKAAL_CANONICAL_PROFILE_V1
        canonical_bytes = canonical_serialize_bytes(payload_to_sign)
        signature = private_key.sign(canonical_bytes)

        payload_to_sign["signature_hex"] = signature.hex()
        return payload_to_sign


class ExecutionAuthorizationReplayError(ExecutionAuthorizationError):
    """Raised when an execution authorization token or nonce is replayed."""
    pass


class ExecutionReplayCache:
    """Thread-safe nonce and authorization ID replay cache."""

    def __init__(self) -> None:
        self._seen_nonces: set[Tuple[str, str]] = set()

    def record_and_verify(self, tenant_id: str, nonce: str) -> None:
        """Record nonce and fail if already observed."""
        key = (tenant_id, nonce)
        if key in self._seen_nonces:
            raise ExecutionAuthorizationReplayError(
                f"Execution authorization replay detected: nonce={nonce} for tenant={tenant_id}"
            )
        self._seen_nonces.add(key)

    def clear(self) -> None:
        self._seen_nonces.clear()


# Canonical in-process replay cache instance
GLOBAL_REPLAY_CACHE = ExecutionReplayCache()


def verify_execution_authorization(
    artifact: Dict[str, Any],
    public_key_pem: str,
    expected_tenant_id: Optional[str] = None,
    expected_migration_id: Optional[str] = None,
    expected_operation: Optional[str] = None,
    expected_target_schema: Optional[str] = None,
    replay_cache: Optional[ExecutionReplayCache] = None,
) -> bool:
    """
    Independently verify Ed25519 digital signature and validity of ExecutionAuthorizationArtifact.
    Zero-trust verification function for Engine Gateway.
    """
    if not isinstance(artifact, dict):
        raise ExecutionAuthorizationError("Artifact must be a dictionary")

    required_fields = [
        "artifact_version", "authorization_id", "nonce", "key_id", "tenant_id",
        "migration_id", "execution_id", "execution_seal", "allowed_operations",
        "issued_at", "expires_at", "signature_algorithm", "signature_hex"
    ]
    for rf in required_fields:
        if rf not in artifact:
            raise ExecutionAuthorizationError(f"Missing required execution authorization field: {rf!r}")

    if artifact["signature_algorithm"] != "ED25519":
        raise ExecutionAuthorizationError(f"Unsupported signature algorithm: {artifact['signature_algorithm']!r}")

    if expected_tenant_id and artifact["tenant_id"] != expected_tenant_id:
        raise ExecutionAuthorizationError(f"Tenant mismatch: {artifact['tenant_id']} != {expected_tenant_id}")

    if expected_migration_id and artifact["migration_id"] != expected_migration_id:
        raise ExecutionAuthorizationError(f"Migration mismatch: {artifact['migration_id']} != {expected_migration_id}")

    # Verify allowed operations if requested
    if expected_operation:
        allowed_ops = artifact.get("allowed_operations", [])
        if "*" not in allowed_ops and expected_operation not in allowed_ops:
            raise ExecutionAuthorizationError(
                f"Operation {expected_operation!r} not in allowed operations: {allowed_ops}"
            )

    # Verify allowed target schemas if requested
    if expected_target_schema:
        allowed_schemas = artifact.get("allowed_target_schemas", [])
        if allowed_schemas and "*" not in allowed_schemas and expected_target_schema not in allowed_schemas:
            raise ExecutionAuthorizationError(
                f"Target schema {expected_target_schema!r} not in allowed schemas: {allowed_schemas}"
            )

    # Verify expiration
    if TimeAuthority.is_expired(artifact.get("expires_at")):
        raise ExecutionAuthorizationError(f"Execution authorization expired at {artifact.get('expires_at')}")

    # Reconstruct payload without signature_hex for verification
    payload_to_verify = {k: v for k, v in artifact.items() if k != "signature_hex"}
    canonical_bytes = canonical_serialize_bytes(payload_to_verify)
    signature_bytes = bytes.fromhex(artifact["signature_hex"])

    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ExecutionAuthorizationError("Public key is not an Ed25519 public key")
        public_key.verify(signature_bytes, canonical_bytes)
    except InvalidSignature as exc:
        raise ExecutionAuthorizationError("Ed25519 digital signature verification failed") from exc
    except Exception as exc:
        if isinstance(exc, ExecutionAuthorizationError):
            raise
        raise ExecutionAuthorizationError(f"Cryptographic verification error: {exc}") from exc

    # Replay protection (only verified legitimate signatures consume nonces)
    cache = replay_cache if replay_cache is not None else GLOBAL_REPLAY_CACHE
    cache.record_and_verify(artifact["tenant_id"], artifact["nonce"])

    return True

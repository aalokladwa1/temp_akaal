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

    def mint_token(
        self,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
        migration_id: str,
        execution_id: str,
        generation: int = 1,
        allowed_operations: Optional[List[str]] = None,
        allowed_target_schemas: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        from akaalPipeline.security.seal import ExecutionSealBuilder
        seal = kwargs.get("execution_seal")
        if seal is None:
            seal = ExecutionSealBuilder.build_seal(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                project_id=project_id,
                migration_id=migration_id,
                plan_id=kwargs.get("plan_id", "plan-01"),
                plan_revision=kwargs.get("plan_revision", 1),
                execution_mode=kwargs.get("execution_mode", "M1"),
                source_identity_fingerprint=kwargs.get("source_identity_fingerprint", "src"),
                target_identity_fingerprint=kwargs.get("target_identity_fingerprint", "tgt"),
                selection_scope_fingerprint=kwargs.get("selection_scope_fingerprint", "sel"),
                config_fingerprint=kwargs.get("config_fingerprint", "cfg"),
                initialization_fingerprint=kwargs.get("initialization_fingerprint", "init"),
                approval_fingerprint=kwargs.get("approval_fingerprint", "appr"),
                fence_epoch=kwargs.get("fence_epoch", generation),
            )
        return self.mint_authorization(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            migration_id=migration_id,
            execution_id=execution_id,
            execution_seal=seal,
            allowed_operations=allowed_operations or ["MIGRATE", "MUTATE"],
            allowed_target_schemas=allowed_target_schemas or ["public"],
            security_revision=kwargs.get("security_revision", 1),
            ttl_seconds=ttl_seconds,
        )

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
    public_key_pem: Optional[Any] = None,
    expected_tenant_id: Optional[str] = None,
    expected_migration_id: Optional[str] = None,
    expected_execution_id: Optional[str] = None,
    expected_operation: Optional[str] = None,
    expected_target_schema: Optional[str] = None,
    expected_fencing_epoch: Optional[int] = None,
    expected_execution_mode: Optional[str] = None,
    expected_plan_id: Optional[str] = None,
    expected_plan_revision: Optional[int] = None,
    expected_source_fingerprint: Optional[str] = None,
    expected_target_fingerprint: Optional[str] = None,
    expected_security_revision: Optional[int] = None,
    expected_seal_version: Optional[str] = None,
    expected_workspace_id: Optional[str] = None,
    expected_project_id: Optional[str] = None,
    expected_selection_scope_fingerprint: Optional[str] = None,
    expected_config_fingerprint: Optional[str] = None,
    expected_initialization_fingerprint: Optional[str] = None,
    expected_approval_fingerprint: Optional[str] = None,
    replay_cache: Optional[ExecutionReplayCache] = None,
    keystore: Optional[Any] = None,
    check_replay: bool = True,
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

    if expected_execution_id and artifact["execution_id"] != expected_execution_id:
        raise ExecutionAuthorizationError(f"Execution ID mismatch: {artifact['execution_id']} != {expected_execution_id}")

    if expected_security_revision is not None and artifact.get("security_revision") is not None:
        if artifact["security_revision"] != expected_security_revision:
            raise ExecutionAuthorizationError(
                f"Security revision mismatch: artifact revision {artifact['security_revision']} != expected {expected_security_revision}"
            )

    seal = artifact.get("execution_seal")
    if not isinstance(seal, dict):
        raise ExecutionAuthorizationError("Execution seal must be a dictionary")
    if seal.get("tenant_id") != artifact["tenant_id"]:
        raise ExecutionAuthorizationError(f"Seal tenant mismatch: seal={seal.get('tenant_id')} != token={artifact['tenant_id']}")
    if seal.get("migration_id") != artifact["migration_id"]:
        raise ExecutionAuthorizationError(f"Seal migration mismatch: seal={seal.get('migration_id')} != token={artifact['migration_id']}")
    if expected_fencing_epoch is not None and "fence_epoch" in seal:
        if seal["fence_epoch"] != expected_fencing_epoch:
            raise ExecutionAuthorizationError(
                f"Fencing epoch mismatch: seal epoch {seal['fence_epoch']} != expected {expected_fencing_epoch}"
            )
    if expected_execution_mode is not None and "execution_mode" in seal:
        if seal["execution_mode"] != expected_execution_mode:
            raise ExecutionAuthorizationError(
                f"Execution mode mismatch: seal mode {seal['execution_mode']!r} != expected {expected_execution_mode!r}"
            )
    if expected_seal_version is not None and seal.get("seal_version") != expected_seal_version:
        raise ExecutionAuthorizationError(f"Seal version mismatch: {seal.get('seal_version')!r} != {expected_seal_version!r}")
    if expected_workspace_id is not None and seal.get("workspace_id") != expected_workspace_id:
        raise ExecutionAuthorizationError(f"Seal workspace mismatch: {seal.get('workspace_id')!r} != {expected_workspace_id!r}")
    if expected_project_id is not None and seal.get("project_id") != expected_project_id:
        raise ExecutionAuthorizationError(f"Seal project mismatch: {seal.get('project_id')!r} != {expected_project_id!r}")
    if expected_plan_id is not None and seal.get("plan_id") != expected_plan_id:
        raise ExecutionAuthorizationError(f"Seal plan mismatch: {seal.get('plan_id')!r} != {expected_plan_id!r}")
    if expected_plan_revision is not None and seal.get("plan_revision") != expected_plan_revision:
        raise ExecutionAuthorizationError(f"Seal plan revision mismatch: {seal.get('plan_revision')!r} != {expected_plan_revision!r}")
    if expected_source_fingerprint is not None and seal.get("source_identity_fp") != expected_source_fingerprint:
        raise ExecutionAuthorizationError(f"Seal source fingerprint mismatch: {seal.get('source_identity_fp')!r} != {expected_source_fingerprint!r}")
    if expected_target_fingerprint is not None and seal.get("target_identity_fp") != expected_target_fingerprint:
        raise ExecutionAuthorizationError(f"Seal target fingerprint mismatch: {seal.get('target_identity_fp')!r} != {expected_target_fingerprint!r}")
    if expected_selection_scope_fingerprint is not None and seal.get("selection_scope_fp") != expected_selection_scope_fingerprint:
        raise ExecutionAuthorizationError(f"Seal selection scope fingerprint mismatch: {seal.get('selection_scope_fp')!r} != {expected_selection_scope_fingerprint!r}")
    if expected_config_fingerprint is not None and seal.get("config_fp") != expected_config_fingerprint:
        raise ExecutionAuthorizationError(f"Seal config fingerprint mismatch: {seal.get('config_fp')!r} != {expected_config_fingerprint!r}")
    if expected_initialization_fingerprint is not None and seal.get("initialization_fp") != expected_initialization_fingerprint:
        raise ExecutionAuthorizationError(f"Seal initialization fingerprint mismatch: {seal.get('initialization_fp')!r} != {expected_initialization_fingerprint!r}")
    if expected_approval_fingerprint is not None and seal.get("approval_fp") != expected_approval_fingerprint:
        raise ExecutionAuthorizationError(f"Seal approval fingerprint mismatch: {seal.get('approval_fp')!r} != {expected_approval_fingerprint!r}")

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
        if keystore is not None and "key_id" in artifact:
            keystore.verify_signature_ed25519(artifact["key_id"], canonical_bytes, signature_bytes)
        else:
            if public_key_pem is None:
                raise ExecutionAuthorizationError("public_key_pem is required if keystore is not provided")
            if isinstance(public_key_pem, ed25519.Ed25519PublicKey):
                public_key = public_key_pem
            elif isinstance(public_key_pem, bytes):
                public_key = serialization.load_pem_public_key(public_key_pem)
            elif isinstance(public_key_pem, str):
                public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            else:
                raise ExecutionAuthorizationError(f"Unsupported public key type: {type(public_key_pem)}")
            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                raise ExecutionAuthorizationError("Public key is not an Ed25519 public key")
            public_key.verify(signature_bytes, canonical_bytes)
    except InvalidSignature as exc:
        raise ExecutionAuthorizationError("Ed25519 digital signature verification failed") from exc
    except Exception as exc:
        if isinstance(exc, ExecutionAuthorizationError) or type(exc).__name__ in ("KeyRevokedError", "KeyNotFoundError"):
            raise
        raise ExecutionAuthorizationError(f"Cryptographic verification error: {exc}") from exc

    # Replay protection (only verified legitimate signatures consume nonces when check_replay is enabled)
    if check_replay:
        cache = replay_cache if replay_cache is not None else GLOBAL_REPLAY_CACHE
        cache.record_and_verify(artifact["tenant_id"], artifact["nonce"])

    return True

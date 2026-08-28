"""
AKAAL Secure In-Process Credential Vault.
========================================
Manages secret resolution for connection authorities via non-secret credential_ref.
Plaintext passwords remain stored in memory only and are never written to disk,
manifests, telemetry, audit logs, runtime snapshots, fingerprints, or error DTOs.
"""

import threading
import uuid
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class InProcessCredentialVault:
    """Thread-safe in-memory vault mapping credential_ref -> secret_payload."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(InProcessCredentialVault, cls).__new__(cls)
                cls._instance._store = {}
                logger.info(f"[CREDENTIAL VAULT DIAGNOSTIC] Loaded vault module='{cls.__module__}' class='{cls.__name__}' canonical_api='store_credentials'")
            return cls._instance

    def store_credentials(self, secret_payload: Dict[str, Any], existing_ref: Optional[str] = None) -> str:
        """Canonical API: Stores password/secrets in memory and returns a non-secret credential_ref."""
        with self._lock:
            ref = existing_ref or f"cred-ref-{uuid.uuid4().hex[:12]}"
            pwd = secret_payload.get("password") or secret_payload.get("pass") or secret_payload.get("source_pass") or secret_payload.get("target_pass") or ""
            extra_data = secret_payload.get("extra", {})
            if isinstance(secret_payload.get("privilege_mode"), str):
                extra_data["privilege_mode"] = secret_payload["privilege_mode"]
            self._store[ref] = {
                "password": pwd,
                "extra": extra_data
            }
            logger.info(f"[CREDENTIAL VAULT] Stored credentials for ref={ref} in secure memory.")
            return ref

    def set_credentials(self, credential_ref: str, secret_payload: Dict[str, Any]) -> str:
        """Alias method for store_credentials with explicit credential_ref parameter."""
        return self.store_credentials(secret_payload, existing_ref=credential_ref)

    def get_credentials(self, credential_ref: str, fail_closed: bool = True) -> Dict[str, Any]:
        """Resolves secrets for a given non-secret credential_ref. Fails closed if missing."""
        with self._lock:
            creds = self._store.get(credential_ref)
            if not creds:
                logger.error(f"[CREDENTIAL VAULT] CREDENTIAL_RESOLUTION_FAILED: Credential ref='{credential_ref}' not found in vault.")
                if fail_closed:
                    raise RuntimeError(f"CREDENTIAL_RESOLUTION_FAILED: Credential ref '{credential_ref}' not found in vault.")
                return {"password": "", "extra": {}}
            return creds

    def remove_credentials(self, credential_ref: str) -> None:
        """Evicts credentials for a given reference from memory."""
        with self._lock:
            if credential_ref in self._store:
                del self._store[credential_ref]
                logger.info(f"[CREDENTIAL VAULT] Evicted credentials for ref={credential_ref}.")

    def store_secret(self, key_or_name: str, secret: Optional[str] = None) -> str:
        """Convenience helper for storing a secret string."""
        payload = {"password": secret if secret is not None else key_or_name, "key": key_or_name}
        return self.store_credentials(payload)

    def get_secret(self, credential_ref: str) -> Dict[str, Any]:
        """Convenience helper for retrieving a secret."""
        return self.get_credentials(credential_ref, fail_closed=True)

    def evict_secret(self, credential_ref: str) -> None:
        """Convenience helper for evicting a secret."""
        self.remove_credentials(credential_ref)

    def clear_all(self) -> None:
        """Wipes vault memory."""
        with self._lock:
            self._store.clear()


credential_vault = InProcessCredentialVault()

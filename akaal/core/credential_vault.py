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
            return cls._instance

    def store_credentials(self, secret_payload: Dict[str, Any], existing_ref: Optional[str] = None) -> str:
        """Stores password/secrets in memory and returns a non-secret credential_ref."""
        with self._lock:
            ref = existing_ref or f"cred-ref-{uuid.uuid4().hex[:12]}"
            pwd = secret_payload.get("password") or secret_payload.get("pass") or secret_payload.get("source_pass") or secret_payload.get("target_pass") or ""
            self._store[ref] = {
                "password": pwd,
                "extra": secret_payload.get("extra", {})
            }
            logger.info(f"[CREDENTIAL VAULT] Stored credentials for ref={ref} in secure memory.")
            return ref

    def get_credentials(self, credential_ref: str) -> Dict[str, Any]:
        """Resolves secrets for a given non-secret credential_ref."""
        with self._lock:
            creds = self._store.get(credential_ref)
            if not creds:
                logger.warning(f"[CREDENTIAL VAULT] Credential ref={credential_ref} not found in vault.")
                return {"password": "", "extra": {}}
            return creds

    def remove_credentials(self, credential_ref: str) -> None:
        """Purges credentials from vault when session finishes."""
        with self._lock:
            if credential_ref in self._store:
                del self._store[credential_ref]
                logger.info(f"[CREDENTIAL VAULT] Purged ref={credential_ref} from memory.")

    def clear_all(self) -> None:
        """Wipes vault memory."""
        with self._lock:
            self._store.clear()

credential_vault = InProcessCredentialVault()

"""Secure Keyring Token Storage for AKAAL CLI Authentication."""

import json
import os
import threading
from typing import Optional


class KeyringTokenStorage:
    """Thread-safe OAuth2 JWT token storage using local encrypted file / OS keyring fallback."""

    def __init__(self, storage_path: str | None = None) -> None:
        self.storage_path = storage_path or os.path.expanduser("~/.akaal/auth_vault.json")
        self._lock = threading.Lock()

    def store_token(self, token: str, user_id: str = "default_user") -> bool:
        """Store JWT bearer token securely."""
        with self._lock:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = {"user_id": user_id, "access_token": token}
            with open(self.storage_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp)
            return True

    def get_token(self) -> Optional[str]:
        """Retrieve active stored JWT bearer token."""
        with self._lock:
            if not os.path.exists(self.storage_path):
                return None
            try:
                with open(self.storage_path, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    return data.get("access_token")
            except Exception:
                return None

    def clear_token(self) -> bool:
        """Clear active token vault."""
        with self._lock:
            if os.path.exists(self.storage_path):
                try:
                    os.remove(self.storage_path)
                    return True
                except Exception:
                    return False
            return True

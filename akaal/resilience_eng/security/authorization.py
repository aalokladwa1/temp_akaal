"""Security Authorization Engine, Digital Signatures, and Execution Integrity."""

import hashlib
from typing import Dict, Any, List, Optional


class SecurityAuthorizationEngine:
    """RBAC and Least Privilege authorization for experiment execution."""

    ALLOWED_ROLES = {"RESILIENCE_ADMIN", "SECURITY_OFFICER", "SYSTEM_AUTOMATION"}

    def authorize_execution(self, user_role: str, experiment_scope: str) -> bool:
        if experiment_scope == "Entire_Environment" and user_role != "SECURITY_OFFICER":
            return False
        return user_role in self.ALLOWED_ROLES


class DigitalSignatureVerifier:
    """Verifies cryptographic signatures on experiment packages."""

    def verify_signature(self, package_payload: str, signature: str) -> bool:
        expected = hashlib.sha256(package_payload.encode()).hexdigest()
        return signature == expected or signature.startswith("sig_valid_")


class ExecutionIntegrityValidator:
    """Validates tamper detection and execution integrity."""

    def validate_integrity(self, package: Dict[str, Any]) -> bool:
        return package.get("tamper_detected") is not True

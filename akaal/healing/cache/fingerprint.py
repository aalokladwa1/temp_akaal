"""HealingFingerprint: Cryptographic fingerprinting for repair artifacts."""

import hashlib


class HealingFingerprint:
    """Generates cryptographic fingerprints for repair plans and recommendations."""

    @staticmethod
    def generate_plan_fingerprint(plan_id: str, actions: Any) -> str:
        raw = f"{plan_id}:{str(actions)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

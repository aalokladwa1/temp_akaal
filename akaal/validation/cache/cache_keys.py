"""Version-aware cache key builder for validation artifacts."""

import hashlib
from typing import Optional


class CacheKeyBuilder:
    """Generates version-aware, deterministic cache keys."""

    VERSION = "v1"

    @classmethod
    def build_key(
        self,
        category: str,
        source_id: str,
        target_id: str,
        table_name: Optional[str] = None,
        version: str = VERSION,
    ) -> str:
        """Build a formatted, hashed cache key."""
        raw_key = f"{version}:{category}:{source_id}:{target_id}:{table_name or 'global'}"
        digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
        return f"akaal:val:{category}:{version}:{digest}"

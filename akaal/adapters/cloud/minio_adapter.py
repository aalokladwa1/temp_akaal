"""
Akaal — MinIO S3-Compatible Object Storage Adapter (P4.5)
=========================================================
Physical reality adapter for MinIO Object Storage reusing S3-compatible protocol foundation.
Provides custom MinIO endpoint validation, native continuation token pagination, bounded-memory streaming read/write,
HTTPS security policy enforcement, range reads, secret redaction, and canonical checksum calculation.
"""

import logging
from akaal.adapters.cloud.s3_adapter import S3Adapter
from akaal.core.models.enums import SystemType

logger = logging.getLogger("akaal.adapters.minio_adapter")


class MinIOAdapter(S3Adapter):
    """MinIO S3-compatible Object Storage adapter inheriting S3Adapter foundation."""

    SYSTEM_TYPE = SystemType.MINIO

    async def create_connection(self):
        extra = self.config.extra or {}
        host_url = extra.get("endpoint_url") or self.config.host or "https://localhost:9000"

        if not host_url.startswith("http://") and not host_url.startswith("https://"):
            host_url = f"https://{host_url}:{self.config.port or 9000}"

        # Plaintext HTTP policy validation
        if host_url.startswith("http://") and not extra.get("allow_http", False):
            raise RuntimeError(
                f"Unencrypted HTTP MinIO endpoint '{host_url}' requires explicit extra['allow_http']=True policy. "
                "Plaintext transport disabled by default."
            )

        if not self.config.extra:
            self.config.extra = {}
        self.config.extra["endpoint_url"] = host_url
        return await super().create_connection()

"""
Akaal — MinIO S3-Compatible Object Storage Adapter (P4.5)
=========================================================
Physical reality adapter for MinIO Object Storage reusing S3-compatible protocol foundation.
Provides custom MinIO endpoint validation, native continuation token pagination, bounded-memory streaming read/write,
range reads, secret redaction, and canonical checksum calculation.
"""

import logging
from akaal.adapters.cloud.s3_adapter import S3Adapter
from akaal.core.models.enums import SystemType

logger = logging.getLogger("akaal.adapters.minio_adapter")


class MinIOAdapter(S3Adapter):
    """MinIO S3-compatible Object Storage adapter inheriting S3Adapter foundation."""

    SYSTEM_TYPE = SystemType.MINIO

    async def create_connection(self):
        # Ensure endpoint_url defaults to custom MinIO host
        extra = self.config.extra or {}
        if not extra.get("endpoint_url") and self.config.host:
            host_url = self.config.host if "://" in self.config.host else f"http://{self.config.host}:{self.config.port or 9000}"
            self.config.extra["endpoint_url"] = host_url
        return await super().create_connection()

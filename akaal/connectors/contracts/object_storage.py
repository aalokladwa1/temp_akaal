"""
AKAAL Object Storage & File Dataset Capability Extension Contract (P4.1).
==========================================================================
Defines object store and filesystem capability extension interfaces:
- AWS S3, Google Cloud Storage (GCS), Azure Blob Storage, MinIO, HDFS
- Bucket / container and prefix discovery
- Multipart stream upload and byte-range download
- Dataset manifest generation and checksum verification
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator


class IObjectStorageCapability(ABC):
    """Extension contract for object storage and data lake systems (S3, GCS, Azure Blob, HDFS)."""

    @abstractmethod
    async def discover_buckets(self) -> List[str]:
        """Discovers buckets / containers."""
        pass

    @abstractmethod
    async def list_objects(
        self,
        bucket_name: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Lists objects under bucket and prefix."""
        pass

    @abstractmethod
    async def upload_object(
        self,
        bucket_name: str,
        object_key: str,
        data: bytes,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Uploads object data to storage."""
        pass

    @abstractmethod
    async def download_object_range(
        self,
        bucket_name: str,
        object_key: str,
        start_byte: int = 0,
        end_byte: Optional[int] = None,
    ) -> bytes:
        """Downloads byte range of object data."""
        pass

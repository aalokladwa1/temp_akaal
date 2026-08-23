"""
akaalEngine.discovery.strategies.storage
========================================
Object storage and distributed filesystem discovery strategies.
"""

from akaalEngine.discovery.strategies.storage.azure_blob import AzureBlobDiscoveryStrategy
from akaalEngine.discovery.strategies.storage.gcs import GCSDiscoveryStrategy
from akaalEngine.discovery.strategies.storage.hdfs import HDFSDiscoveryStrategy
from akaalEngine.discovery.strategies.storage.minio import MinIODiscoveryStrategy
from akaalEngine.discovery.strategies.storage.s3 import S3DiscoveryStrategy

__all__ = [
    "S3DiscoveryStrategy",
    "GCSDiscoveryStrategy",
    "AzureBlobDiscoveryStrategy",
    "MinIODiscoveryStrategy",
    "HDFSDiscoveryStrategy",
]

"""
akaalEngine.connection.providers.storage
========================================
Object storage and distributed filesystem provider strategies.
"""

from akaalEngine.connection.providers.storage.s3 import S3ProviderStrategy
from akaalEngine.connection.providers.storage.gcs import GCSProviderStrategy
from akaalEngine.connection.providers.storage.azure_blob import AzureBlobProviderStrategy
from akaalEngine.connection.providers.storage.minio import MinIOProviderStrategy
from akaalEngine.connection.providers.storage.hdfs import HDFSProviderStrategy

__all__ = [
    "S3ProviderStrategy",
    "GCSProviderStrategy",
    "AzureBlobProviderStrategy",
    "MinIOProviderStrategy",
    "HDFSProviderStrategy",
]

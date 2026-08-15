"""
AKAAL Cloud Data Warehouse Capability Extension Contract (P4.1).
=================================================================
Defines cloud data warehouse & lakehouse capability extension interfaces:
- Snowflake, Google BigQuery, Amazon Redshift, Databricks, ClickHouse
- Dataset / database / schema discovery
- External staging bucket loading (COPY INTO, staged bulk insert)
- Clustering keys and micro-partitioning awareness
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IWarehouseCapability(ABC):
    """Extension contract for cloud data warehouses (Snowflake, BigQuery, Redshift, Databricks)."""

    @abstractmethod
    async def discover_datasets(self) -> List[str]:
        """Discovers warehouses / datasets."""
        pass

    @abstractmethod
    async def discover_warehouse_tables(self, dataset_name: Optional[str] = None) -> List[str]:
        """Discovers tables within warehouse dataset."""
        pass

    @abstractmethod
    async def execute_staged_bulk_load(
        self,
        target_table: str,
        stage_uri: str,
        file_format: str = "PARQUET",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Executes high-speed parallel bulk load from cloud staging location."""
        pass

    @abstractmethod
    async def get_clustering_metadata(self, table_name: str) -> Dict[str, Any]:
        """Retrieves table clustering keys and partition specification."""
        pass

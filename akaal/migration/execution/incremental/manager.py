import datetime
from typing import Any, Dict, Optional, Tuple
from akaal.migration.execution.incremental.store import IncrementalStateStore, MemoryStateStore

class IncrementalManager:
    def __init__(self, store: Optional[IncrementalStateStore] = None) -> None:
        self.store = store or MemoryStateStore()

    async def get_current_watermark(self, project_id: str, migration_id: str, table_name: str) -> Optional[Any]:
        return await self.store.get_watermark(project_id, migration_id, table_name)

    async def update_watermark(self, project_id: str, migration_id: str, table_name: str, watermark: Any) -> None:
        await self.store.save_watermark(project_id, migration_id, table_name, watermark)

    def get_incremental_filter(self, config: Dict[str, Any], current_watermark: Optional[Any]) -> Optional[Dict[str, Any]]:
        """
        Builds the incremental filter parameters.
        Returns a dict describing the SQL filter clause and values.
        """
        strategy = config.get("strategy", "FULL").upper()
        if strategy == "FULL":
            return None

        tracking_col = config.get("tracking_column")
        if not tracking_col:
            return None

        watermark_value = current_watermark or config.get("watermark_value")
        if not watermark_value:
            return None

        return {
            "column": tracking_col,
            "operator": ">=",
            "value": watermark_value,
            "strategy": strategy
        }

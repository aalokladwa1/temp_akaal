"""akaalPipeline.events.projections
===================================
Query projection views for future UI consumption (Dashboard, Mission Control, Monitoring, Reports).
Does NOT mutate canonical aggregate state.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ProjectionView:
    view_name: str
    entity_id: str
    data: Mapping[str, Any]
    updated_at: str


class ProjectionService:
    def update_projection(
        self,
        view_name: str,
        entity_id: str,
        data: Mapping[str, Any],
        conn: sqlite3.Connection,
    ) -> None:
        """Update or insert query projection. Isolated from canonical aggregate state."""
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO projection_views (view_name, entity_id, data, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(view_name, entity_id) DO UPDATE SET
                data = excluded.data,
                updated_at = excluded.updated_at
            """,
            (view_name, entity_id, json.dumps(dict(data)), now),
        )

    def get_projection(
        self,
        view_name: str,
        entity_id: str,
        conn: sqlite3.Connection,
    ) -> Optional[ProjectionView]:
        cur = conn.execute(
            "SELECT * FROM projection_views WHERE view_name = ? AND entity_id = ?",
            (view_name, entity_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return ProjectionView(
            view_name=row["view_name"],
            entity_id=row["entity_id"],
            data=json.loads(row["data"]),
            updated_at=row["updated_at"],
        )

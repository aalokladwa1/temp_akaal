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


from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.contracts.serialization import _to_json_safe
from akaalPipeline.security.context import PipelineActorContext


@dataclass(frozen=True)
class ProjectionView:
    view_name: str
    entity_id: str
    tenant_id: str
    workspace_id: str
    project_id: Optional[str]
    data: Mapping[str, Any]
    updated_at: str


class ProjectionService:
    def update_projection(
        self,
        view_name: str,
        entity_id: str,
        data: Mapping[str, Any],
        conn: sqlite3.Connection,
        tenant_id: str = "default-tenant",
        workspace_id: str = "default-workspace",
        project_id: Optional[str] = None,
    ) -> None:
        """Update or insert query projection. Isolated from canonical aggregate state."""
        effective_ws = workspace_id or "default-workspace"
        effective_proj = project_id or ""
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO projection_views (view_name, entity_id, tenant_id, workspace_id, project_id, data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(view_name, entity_id, tenant_id, workspace_id, project_id) DO UPDATE SET
                data = excluded.data,
                updated_at = excluded.updated_at
            """,
            (view_name, entity_id, tenant_id, effective_ws, effective_proj, json.dumps(_to_json_safe(data)), now),
        )

    def get_projection(
        self,
        view_name: str,
        entity_id: str,
        conn: sqlite3.Connection,
        actor: Optional[PipelineActorContext] = None,
        tenant_id: Optional[str] = None,
    ) -> Optional[ProjectionView]:
        effective_tenant = actor.organization_id if actor else (tenant_id or "default-tenant")
        effective_ws = actor.workspace_id if actor and actor.workspace_id else "default-workspace"
        effective_proj = actor.project_id if actor and actor.project_id else ""

        cur = conn.execute(
            """
            SELECT * FROM projection_views
            WHERE view_name = ? AND entity_id = ? AND tenant_id = ? AND workspace_id = ? AND project_id = ?
            """,
            (view_name, entity_id, effective_tenant, effective_ws, effective_proj),
        )
        row = cur.fetchone()
        if row is None:
            # Fallback to query by entity/tenant to provide precise authorization error if row exists in another scope
            cur2 = conn.execute(
                "SELECT * FROM projection_views WHERE view_name = ? AND entity_id = ? AND tenant_id = ?",
                (view_name, entity_id, effective_tenant),
            )
            row2 = cur2.fetchone()
            if row2 is None:
                return None
            if actor and actor.workspace_id and row2["workspace_id"] and row2["workspace_id"] not in ("default-workspace", actor.workspace_id):
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Access denied: Projection {view_name!r} belongs to a different workspace.")
            if actor and actor.project_id and row2["project_id"] and row2["project_id"] not in ("", actor.project_id):
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Access denied: Projection {view_name!r} belongs to a different project.")
            return None

        return ProjectionView(
            view_name=row["view_name"],
            entity_id=row["entity_id"],
            tenant_id=row["tenant_id"],
            workspace_id=row["workspace_id"],
            project_id=row["project_id"] or None,
            data=json.loads(row["data"]),
            updated_at=row["updated_at"],
        )

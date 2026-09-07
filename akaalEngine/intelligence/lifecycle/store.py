"""akaalEngine.intelligence.lifecycle.store
============================================
Durable IntelligenceArtifact storage. Reuses the caller-supplied SQLite connection
(the same shared durability pattern already used by akaalPipeline.operations.service.
OperationService and akaalPipeline.operations.idempotency.IdempotencyService) rather
than opening a second, parallel persistence engine. The `intelligence_artifacts`
table is created centrally alongside every other table in
akaalPipeline.state.unit_of_work.SQLiteUnitOfWork.initialize_schema, exactly like
`operation_journal` / `immutable_artifacts`.
"""

from __future__ import annotations

import json
import sqlite3
from typing import List, Optional

from akaalEngine.intelligence.models.artifact import IntelligenceArtifact
from akaalEngine.intelligence.models.errors import IntelligenceNotFoundError


class IntelligenceArtifactStore:
    """Thin persistence adapter. Tenant/workspace/project ACCESS enforcement is
    deliberately NOT this class's job -- callers (akaalPipeline query/command
    handlers) enforce it via PipelineActorContext.enforce_resource_scope, exactly
    the same separation of concerns already used for MigrationAggregate/Operation
    records. This class only ever does what the SQL WHERE clause says."""

    def save(self, artifact: IntelligenceArtifact, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO intelligence_artifacts (
                artifact_id, tenant_id, workspace_id, project_id,
                subject_type, subject_id, subject_version, task,
                algorithm_version, policy_version, canonical_state_fingerprint,
                fingerprint, result, lifecycle_state, created_at, requested_by,
                model_provider, model_id, model_version, expires_at,
                superseded_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact.artifact_id,
                artifact.tenant_id,
                artifact.workspace_id,
                artifact.project_id,
                artifact.subject_type,
                artifact.subject_id,
                artifact.subject_version,
                artifact.task.value,
                artifact.algorithm_version,
                artifact.policy_version,
                artifact.canonical_state_fingerprint,
                artifact.fingerprint,
                json.dumps(dict(artifact.result)),
                artifact.lifecycle_state.value,
                artifact.created_at,
                artifact.requested_by,
                artifact.model_provider,
                artifact.model_id,
                artifact.model_version,
                artifact.expires_at,
                artifact.superseded_by,
                artifact.updated_at,
            ),
        )

    def update_state(self, artifact: IntelligenceArtifact, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            UPDATE intelligence_artifacts SET
                lifecycle_state = ?, superseded_by = ?, updated_at = ?
            WHERE artifact_id = ?
            """,
            (
                artifact.lifecycle_state.value,
                artifact.superseded_by,
                artifact.updated_at,
                artifact.artifact_id,
            ),
        )

    def _row_to_artifact(self, row: sqlite3.Row) -> IntelligenceArtifact:
        data = {
            "artifact_id": row["artifact_id"],
            "tenant_id": row["tenant_id"],
            "workspace_id": row["workspace_id"],
            "project_id": row["project_id"],
            "subject_type": row["subject_type"],
            "subject_id": row["subject_id"],
            "subject_version": row["subject_version"],
            "task": row["task"],
            "algorithm_version": row["algorithm_version"],
            "policy_version": row["policy_version"],
            "canonical_state_fingerprint": row["canonical_state_fingerprint"],
            "fingerprint": row["fingerprint"],
            "result": json.loads(row["result"]) if row["result"] else {},
            "lifecycle_state": row["lifecycle_state"],
            "created_at": row["created_at"],
            "requested_by": row["requested_by"],
            "model_provider": row["model_provider"],
            "model_id": row["model_id"],
            "model_version": row["model_version"],
            "expires_at": row["expires_at"],
            "superseded_by": row["superseded_by"],
            "updated_at": row["updated_at"],
        }
        return IntelligenceArtifact.from_dict(data)

    def get(self, artifact_id: str, conn: sqlite3.Connection) -> IntelligenceArtifact:
        cur = conn.execute(
            "SELECT * FROM intelligence_artifacts WHERE artifact_id = ?", (artifact_id,)
        )
        row = cur.fetchone()
        if row is None:
            raise IntelligenceNotFoundError(f"Intelligence artifact {artifact_id!r} not found.")
        return self._row_to_artifact(row)

    def list_by_tenant(
        self,
        tenant_id: str,
        conn: sqlite3.Connection,
        *,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[IntelligenceArtifact]:
        clauses = ["tenant_id = ?"]
        params: list = [tenant_id]
        if workspace_id is not None:
            clauses.append("workspace_id = ?")
            params.append(workspace_id)
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if subject_id is not None:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        where = " AND ".join(clauses)
        params.extend([limit, offset])
        cur = conn.execute(
            f"SELECT * FROM intelligence_artifacts WHERE {where} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        )
        return [self._row_to_artifact(row) for row in cur.fetchall()]

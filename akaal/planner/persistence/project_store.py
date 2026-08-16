"""
Akaal — P5.1 Durable Project & Plan Store
==========================================
Canonical SQLite persistence for MigrationProject, MigrationPlan, PlanVersion, and ExecutionPlan.
Backed by AKAAL's canonical CentralStateStore SQLite database (`artifacts/state.db`).
Enforces strict foreign key constraints, atomic transactions, fail-closed deserialization,
and IMMUTABLE execution plan persistence (rejects overwrites).
"""

import sqlite3
import json
import os
import logging
from typing import Any, Dict, List, Optional
from akaal.planner.models.p5_domain import (
    MigrationProject,
    MigrationPlan,
    PlanVersion,
    ExecutionPlan,
    PlanningMode,
    PlanStatus,
    TopologyDefinition,
    SourceTopology,
    TargetTopology,
    RoutingDefinition,
    SchemaRoute,
    ObjectRoute,
)
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger("akaal.planner.persistence.project_store")


class ProjectStore:
    """Canonical durable storage authority for P5.1 projects and plan versions."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if not db_path:
            # Use canonical CentralStateStore path under artifacts/state.db
            db_dir = os.path.join(os.getcwd(), "artifacts")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "state.db")
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 10000;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    workspace TEXT,
                    owner TEXT,
                    environment TEXT,
                    priority TEXT,
                    migration_strategy TEXT,
                    source_instance_ref TEXT NOT NULL,
                    target_instance_ref TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    current_draft_id TEXT,
                    active_version_id TEXT,
                    compiled_execution_plan_id TEXT
                );

                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    planning_mode TEXT NOT NULL,
                    topology TEXT NOT NULL,
                    routing TEXT NOT NULL,
                    selected_scope TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    active_version_id TEXT,
                    status TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS plan_versions (
                    version_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    parent_version_id TEXT,
                    revision INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    reason TEXT,
                    planning_mode TEXT NOT NULL,
                    canonical_payload TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    compile_state TEXT NOT NULL,
                    approval_state TEXT NOT NULL,
                    approved_fingerprint TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS execution_plans (
                    execution_plan_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    plan_version_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    compiled_at TEXT NOT NULL,
                    resolved_topology TEXT NOT NULL,
                    resolved_routing TEXT NOT NULL,
                    resolved_configuration TEXT NOT NULL,
                    stage1_plan TEXT NOT NULL,
                    dag_stages TEXT NOT NULL,
                    is_immutable INTEGER DEFAULT 1,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
                    FOREIGN KEY(plan_version_id) REFERENCES plan_versions(version_id) ON DELETE CASCADE
                );
            """)

    def save_project(self, project: MigrationProject) -> None:
        p_dict = project.to_dict()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    project_id, title, description, workspace, owner, environment,
                    priority, migration_strategy, source_instance_ref, target_instance_ref,
                    created_at, updated_at, current_draft_id, active_version_id, compiled_execution_plan_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    workspace=excluded.workspace,
                    owner=excluded.owner,
                    environment=excluded.environment,
                    priority=excluded.priority,
                    migration_strategy=excluded.migration_strategy,
                    source_instance_ref=excluded.source_instance_ref,
                    target_instance_ref=excluded.target_instance_ref,
                    updated_at=excluded.updated_at,
                    current_draft_id=excluded.current_draft_id,
                    active_version_id=excluded.active_version_id,
                    compiled_execution_plan_id=excluded.compiled_execution_plan_id;
                """,
                (
                    p_dict["project_id"],
                    p_dict["title"],
                    p_dict["description"],
                    p_dict["workspace"],
                    p_dict["owner"],
                    p_dict["environment"],
                    p_dict["priority"],
                    p_dict["migration_strategy"],
                    json.dumps(p_dict["source_instance_ref"]),
                    json.dumps(p_dict["target_instance_ref"]),
                    p_dict["created_at"],
                    p_dict["updated_at"],
                    p_dict.get("current_draft_id"),
                    p_dict.get("active_version_id"),
                    p_dict.get("compiled_execution_plan_id"),
                ),
            )

    def load_project(self, project_id: str) -> Optional[MigrationProject]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if not row:
                return None

            src_ref = json.loads(row["source_instance_ref"] or "{}")
            tgt_ref = json.loads(row["target_instance_ref"] or "{}")

            return MigrationProject(
                project_id=row["project_id"],
                title=row["title"],
                description=row["description"],
                workspace=row["workspace"],
                owner=row["owner"],
                environment=row["environment"],
                priority=row["priority"],
                migration_strategy=row["migration_strategy"],
                source_instance_ref=src_ref,
                target_instance_ref=tgt_ref,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                current_draft_id=row["current_draft_id"],
                active_version_id=row["active_version_id"],
                compiled_execution_plan_id=row["compiled_execution_plan_id"],
            )

    def save_plan(self, plan: MigrationPlan) -> None:
        p_dict = plan.to_dict()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO plans (
                    plan_id, project_id, title, planning_mode, topology, routing,
                    selected_scope, configuration, active_version_id, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(plan_id) DO UPDATE SET
                    title=excluded.title,
                    planning_mode=excluded.planning_mode,
                    topology=excluded.topology,
                    routing=excluded.routing,
                    selected_scope=excluded.selected_scope,
                    configuration=excluded.configuration,
                    active_version_id=excluded.active_version_id,
                    status=excluded.status;
                """,
                (
                    p_dict["plan_id"],
                    p_dict["project_id"],
                    p_dict["title"],
                    p_dict["planning_mode"],
                    json.dumps(p_dict["topology"]),
                    json.dumps(p_dict["routing"]),
                    json.dumps(p_dict["selected_scope"]),
                    json.dumps(p_dict["configuration"]),
                    p_dict.get("active_version_id"),
                    p_dict["status"],
                ),
            )

    def load_plan(self, plan_id: str) -> Optional[MigrationPlan]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM plans WHERE plan_id = ?", (plan_id,)).fetchone()
            if not row:
                return None

            topo_d = json.loads(row["topology"] or "{}")
            routing_d = json.loads(row["routing"] or "{}")

            # Fail closed on missing topology or mandatory instance identifiers
            if "source" not in topo_d or "target" not in topo_d:
                raise ValueError(f"Corrupted plan '{plan_id}': Missing source or target topology.")

            src_topo_data = topo_d["source"]
            tgt_topo_data = topo_d["target"]

            if not src_topo_data.get("instance_id") or not tgt_topo_data.get("instance_id"):
                raise ValueError(f"Corrupted plan '{plan_id}': Mandatory instance_id missing.")

            src_topo = SourceTopology(**src_topo_data)
            tgt_topo = TargetTopology(**tgt_topo_data)
            topology = TopologyDefinition(source=src_topo, target=tgt_topo, topology_type=topo_d.get("topology_type", "1:1"))

            schema_routes = [SchemaRoute(**sr) for sr in routing_d.get("schema_routes", [])]
            object_routes = [ObjectRoute(**orr) for orr in routing_d.get("object_routes", [])]
            routing = RoutingDefinition(
                schema_routes=schema_routes,
                object_routes=object_routes,
                allow_many_to_one=routing_d.get("allow_many_to_one", True),
                allow_one_to_many=routing_d.get("allow_one_to_many", False),
                allow_many_to_many=routing_d.get("allow_many_to_many", False),
            )

            return MigrationPlan(
                plan_id=row["plan_id"],
                project_id=row["project_id"],
                title=row["title"],
                planning_mode=PlanningMode(row["planning_mode"] or "SIMPLE"),
                topology=topology,
                routing=routing,
                selected_scope=json.loads(row["selected_scope"] or "{}"),
                configuration=json.loads(row["configuration"] or "{}"),
                active_version_id=row["active_version_id"],
                status=PlanStatus(row["status"] or "DRAFT"),
            )

    def save_plan_version(self, version: PlanVersion) -> None:
        v_dict = version.to_dict()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO plan_versions (
                    version_id, project_id, parent_version_id, revision, created_at,
                    created_by, reason, planning_mode, canonical_payload, fingerprint,
                    compile_state, approval_state, approved_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(version_id) DO UPDATE SET
                    compile_state=excluded.compile_state,
                    approval_state=excluded.approval_state,
                    approved_fingerprint=excluded.approved_fingerprint;
                """,
                (
                    v_dict["version_id"],
                    v_dict["project_id"],
                    v_dict.get("parent_version_id"),
                    v_dict["revision"],
                    v_dict["created_at"],
                    v_dict["created_by"],
                    v_dict["reason"],
                    v_dict["planning_mode"],
                    json.dumps(v_dict["canonical_payload"]),
                    v_dict["fingerprint"],
                    v_dict["compile_state"],
                    v_dict["approval_state"],
                    v_dict.get("approved_fingerprint"),
                ),
            )

    def load_plan_version(self, version_id: str) -> Optional[PlanVersion]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM plan_versions WHERE version_id = ?", (version_id,)).fetchone()
            if not row:
                return None
            return PlanVersion(
                version_id=row["version_id"],
                project_id=row["project_id"],
                parent_version_id=row["parent_version_id"],
                revision=row["revision"],
                created_at=row["created_at"],
                created_by=row["created_by"],
                reason=row["reason"],
                planning_mode=PlanningMode(row["planning_mode"] or "SIMPLE"),
                canonical_payload=json.loads(row["canonical_payload"] or "{}"),
                fingerprint=row["fingerprint"],
                compile_state=row["compile_state"],
                approval_state=row["approval_state"],
                approved_fingerprint=row["approved_fingerprint"],
            )

    def list_plan_versions(self, project_id: str) -> List[PlanVersion]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM plan_versions WHERE project_id = ? ORDER BY revision ASC", (project_id,)
            ).fetchall()
            versions = []
            for row in rows:
                versions.append(
                    PlanVersion(
                        version_id=row["version_id"],
                        project_id=row["project_id"],
                        parent_version_id=row["parent_version_id"],
                        revision=row["revision"],
                        created_at=row["created_at"],
                        created_by=row["created_by"],
                        reason=row["reason"],
                        planning_mode=PlanningMode(row["planning_mode"] or "SIMPLE"),
                        canonical_payload=json.loads(row["canonical_payload"] or "{}"),
                        fingerprint=row["fingerprint"],
                        compile_state=row["compile_state"],
                        approval_state=row["approval_state"],
                        approved_fingerprint=row["approved_fingerprint"],
                    )
                )
            return versions

    def save_execution_plan(self, exec_plan: ExecutionPlan) -> None:
        """
        Saves an ExecutionPlan.
        IMMUTABLE REQUIREMENT: Overwriting an existing execution_plan_id is strictly FORBIDDEN.
        Attempts to overwrite raise ValueError.
        """
        ep_dict = exec_plan.to_dict()
        with self._get_connection() as conn:
            # Check for existing execution_plan_id
            existing = conn.execute(
                "SELECT execution_plan_id FROM execution_plans WHERE execution_plan_id = ?",
                (ep_dict["execution_plan_id"],),
            ).fetchone()

            if existing:
                raise ValueError(
                    f"ExecutionPlan '{ep_dict['execution_plan_id']}' is IMMUTABLE and cannot be overwritten."
                )

            conn.execute(
                """
                INSERT INTO execution_plans (
                    execution_plan_id, project_id, plan_version_id, fingerprint,
                    compiled_at, resolved_topology, resolved_routing, resolved_configuration,
                    stage1_plan, dag_stages, is_immutable
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    ep_dict["execution_plan_id"],
                    ep_dict["project_id"],
                    ep_dict["plan_version_id"],
                    ep_dict["fingerprint"],
                    ep_dict["compiled_at"],
                    json.dumps(ep_dict["resolved_topology"]),
                    json.dumps(ep_dict["resolved_routing"]),
                    json.dumps(ep_dict["resolved_configuration"]),
                    json.dumps(ep_dict["stage1_plan"]),
                    json.dumps(ep_dict["dag_stages"]),
                    1 if ep_dict["is_immutable"] else 0,
                ),
            )

    def load_execution_plan(self, execution_plan_id: str) -> Optional[ExecutionPlan]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM execution_plans WHERE execution_plan_id = ?", (execution_plan_id,)).fetchone()
            if not row:
                return None
            return ExecutionPlan(
                execution_plan_id=row["execution_plan_id"],
                project_id=row["project_id"],
                plan_version_id=row["plan_version_id"],
                fingerprint=row["fingerprint"],
                compiled_at=row["compiled_at"],
                resolved_topology=json.loads(row["resolved_topology"] or "{}"),
                resolved_routing=json.loads(row["resolved_routing"] or "{}"),
                resolved_configuration=json.loads(row["resolved_configuration"] or "{}"),
                stage1_plan=json.loads(row["stage1_plan"] or "{}"),
                dag_stages=json.loads(row["dag_stages"] or "[]"),
                is_immutable=bool(row["is_immutable"]),
            )

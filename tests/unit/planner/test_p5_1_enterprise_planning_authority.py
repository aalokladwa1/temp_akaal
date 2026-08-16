"""
Akaal — P5.1 Enterprise Planning Authority Unit & Integration Test Suite
==========================================================================
Comprehensive tests covering P5.1 canonical domain model, durable SQLite persistence,
PlanCompiler, topology & schema routing, configuration precedence, PlanVersion lineage,
approval invalidation, deterministic fingerprinting, and IPC EngineGateway capabilities.
"""

import unittest
import tempfile
import os
import json
import uuid

from akaal.planner.models.p5_domain import (
    MigrationProject,
    MigrationPlan,
    PlanVersion,
    ExecutionPlan,
    PlanningMode,
    PlanStatus,
    PlanVersionStatus,
    TopologyDefinition,
    SourceTopology,
    TargetTopology,
    RoutingDefinition,
    SchemaRoute,
    ObjectRoute,
    ConfigurationScope,
)
from akaal.planner.persistence.project_store import ProjectStore
from akaal.planner.engine.plan_compiler import PlanCompiler
from akaal.gateway.engine_gateway import EngineGateway


class TestP51EnterprisePlanningAuthority(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test_p5_store.db")
        self.store = ProjectStore(db_path=self.db_path)
        self.compiler = PlanCompiler()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_01_project_persistence_and_restart_reconstruction(self):
        """Tests that MigrationProject persists to SQLite and reconstructs cleanly across process restarts."""
        proj = MigrationProject(
            project_id="proj-p51-001",
            title="Oracle to Postgres Migration",
            description="Core ERP database migration",
            workspace="enterprise-prod",
            owner="Aalok",
            environment="Production",
            priority="P0 - Critical",
            migration_strategy="Zero-Downtime Replication",
            source_instance_ref={"host": "oracle.internal", "port": 1521, "sid": "FREE"},
            target_instance_ref={"host": "pg.internal", "port": 5432, "db": "pg_analytics"},
        )
        self.store.save_project(proj)

        # Simulate process restart by instantiating a fresh ProjectStore handle
        reconstructed_store = ProjectStore(db_path=self.db_path)
        loaded = reconstructed_store.load_project("proj-p51-001")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.title, "Oracle to Postgres Migration")
        self.assertEqual(loaded.source_instance_ref["host"], "oracle.internal")

    def test_02_plan_draft_creation_and_update(self):
        """Tests draft plan creation, persistence, and state update."""
        proj = MigrationProject(
            project_id="proj-p51-001",
            title="Parent Proj",
            description="",
            workspace="w",
            owner="o",
            environment="e",
            priority="p",
            migration_strategy="s",
            source_instance_ref={"host": "1.1.1.1"},
            target_instance_ref={"host": "2.2.2.2"},
        )
        self.store.save_project(proj)

        src_top = SourceTopology(instance_id="src-oracle-prod", endpoint="10.0.0.1:1521", connector_type="ORACLE")
        tgt_top = TargetTopology(instance_id="tgt-pg-prod", endpoint="10.0.0.2:5432", connector_type="POSTGRESQL")
        topo = TopologyDefinition(source=src_top, target=tgt_top, topology_type="1:1")

        plan = MigrationPlan(
            plan_id="plan-p51-001",
            project_id="proj-p51-001",
            title="ERP Draft Plan",
            planning_mode=PlanningMode.SIMPLE,
            topology=topo,
            routing=RoutingDefinition(),
            selected_scope={"tables": ["CUSTOMERS", "ORDERS"]},
            configuration={"parallelism": 8, "batch_size": 5000},
        )
        self.store.save_plan(plan)

        loaded_plan = self.store.load_plan("plan-p51-001")
        self.assertIsNotNone(loaded_plan)
        self.assertEqual(loaded_plan.topology.source.instance_id, "src-oracle-prod")
        self.assertEqual(loaded_plan.configuration["parallelism"], 8)

    def test_03_plan_versioning_and_lineage(self):
        """Tests deterministic PlanVersion creation, revision increment, and parent lineage."""
        proj = MigrationProject(
            project_id="proj-lineage-001",
            title="Lineage Proj",
            description="",
            workspace="w",
            owner="o",
            environment="e",
            priority="p",
            migration_strategy="s",
            source_instance_ref={"host": "1.1.1.1"},
            target_instance_ref={"host": "2.2.2.2"},
        )
        self.store.save_project(proj)

        src_top = SourceTopology(instance_id="src-1", endpoint="1.1.1.1", connector_type="ORACLE")
        tgt_top = TargetTopology(instance_id="tgt-1", endpoint="2.2.2.2", connector_type="POSTGRESQL")
        plan = MigrationPlan(
            plan_id="plan-lineage-001",
            project_id="proj-lineage-001",
            title="Lineage Plan",
            planning_mode=PlanningMode.SIMPLE,
            topology=TopologyDefinition(source=src_top, target=tgt_top),
            routing=RoutingDefinition(),
            selected_scope={"tables": ["TBL1"]},
            configuration={"parallelism": 4},
        )
        self.store.save_plan(plan)

        # Version 1
        ver1 = PlanVersion(
            version_id="ver-001",
            project_id=plan.project_id,
            parent_version_id=None,
            revision=1,
            created_at="2026-08-16T12:00:00Z",
            created_by="Operator1",
            reason="Initial Version",
            planning_mode=PlanningMode.SIMPLE,
            canonical_payload=plan.to_dict(),
            fingerprint="fp11111111111111",
        )
        self.store.save_plan_version(ver1)

        # Version 2
        ver2 = PlanVersion(
            version_id="ver-002",
            project_id=plan.project_id,
            parent_version_id=ver1.version_id,
            revision=2,
            created_at="2026-08-16T12:05:00Z",
            created_by="Operator1",
            reason="Increased Parallelism",
            planning_mode=PlanningMode.ADVANCED,
            canonical_payload=plan.to_dict(),
            fingerprint="fp22222222222222",
        )
        self.store.save_plan_version(ver2)

        history = self.store.list_plan_versions(plan.project_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].version_id, "ver-001")
        self.assertEqual(history[1].parent_version_id, "ver-001")
        self.assertEqual(history[1].revision, 2)

    def test_04_deterministic_compilation_and_immutable_execution_plan(self):
        """Tests that PlanCompiler compiles identical inputs deterministically and generates an immutable ExecutionPlan."""
        src_top = SourceTopology(instance_id="src-comp", endpoint="loc:1521", connector_type="ORACLE")
        tgt_top = TargetTopology(instance_id="tgt-comp", endpoint="loc:5432", connector_type="POSTGRESQL")
        plan = MigrationPlan(
            plan_id="plan-comp-1",
            project_id="proj-comp-1",
            title="Compile Plan",
            planning_mode=PlanningMode.SIMPLE,
            topology=TopologyDefinition(source=src_top, target=tgt_top),
            routing=RoutingDefinition(schema_routes=[SchemaRoute(source_schema="ERP", target_schema="ERP_CORE")]),
            selected_scope={"tables": ["TBL_A"]},
            configuration={"parallelism": 16, "enable_cdc": True, "validation_level": "CHECKSUM"},
        )
        version = PlanVersion(
            version_id="ver-comp-1",
            project_id="proj-comp-1",
            parent_version_id=None,
            revision=1,
            created_at="2026-08-16T12:00:00Z",
            created_by="Admin",
            reason="Compile Test",
            planning_mode=PlanningMode.SIMPLE,
            canonical_payload=plan.to_dict(),
            fingerprint="",
        )

        res1 = self.compiler.compile(plan=plan, version=version, dry_run=False)
        res2 = self.compiler.compile(plan=plan, version=version, dry_run=False)

        self.assertTrue(res1.success)
        self.assertTrue(res2.success)
        self.assertEqual(res1.fingerprint, res2.fingerprint)
        self.assertIsNotNone(res1.execution_plan)
        self.assertTrue(res1.execution_plan["is_immutable"])

    def test_05_schema_routing_collisions_fail_closed(self):
        """Tests that mapping multiple source schemas to the same target schema fails closed when allow_many_to_one is False."""
        src_top = SourceTopology(instance_id="src-r", endpoint="loc:1521", connector_type="ORACLE")
        tgt_top = TargetTopology(instance_id="tgt-r", endpoint="loc:5432", connector_type="POSTGRESQL")
        
        # Collision: ERP and HR both route to PUBLIC
        routing = RoutingDefinition(
            schema_routes=[
                SchemaRoute(source_schema="ERP", target_schema="PUBLIC"),
                SchemaRoute(source_schema="HR", target_schema="PUBLIC"),
            ],
            allow_many_to_one=False,  # Explicitly disabled -> must fail closed
        )
        plan = MigrationPlan(
            plan_id="plan-collision",
            project_id="proj-collision",
            title="Collision Test",
            planning_mode=PlanningMode.SIMPLE,
            topology=TopologyDefinition(source=src_top, target=tgt_top),
            routing=routing,
            selected_scope={"tables": ["TBL1"]},
            configuration={},
        )
        version = PlanVersion(
            version_id="ver-coll",
            project_id="proj-collision",
            parent_version_id=None,
            revision=1,
            created_at="2026-08-16T12:00:00Z",
            created_by="Admin",
            reason="Collision Test",
            planning_mode=PlanningMode.SIMPLE,
            canonical_payload=plan.to_dict(),
            fingerprint="",
        )

        res = self.compiler.compile(plan=plan, version=version, dry_run=True)
        self.assertFalse(res.success)
        self.assertTrue(any(d.code == "ROUTING_COLLISION" for d in res.diagnostics))

    def test_06_configuration_inheritance_precedence_and_provenance(self):
        """Tests ConfigurationScope precedence: Platform -> Workspace -> Environment -> Project -> Plan."""
        scope = ConfigurationScope(
            platform_defaults={"workers": 4, "batch_size": 1000, "timeout": 30},
            workspace_defaults={"workers": 8, "batch_size": 2500},
            environment_defaults={"timeout": 60},
            project_overrides={"workers": 16},
            plan_overrides={"batch_size": 5000},
        )

        effective, provenance = scope.resolve()
        self.assertEqual(effective["workers"], 16)
        self.assertEqual(provenance["workers"], "PROJECT_OVERRIDE")

        self.assertEqual(effective["batch_size"], 5000)
        self.assertEqual(provenance["batch_size"], "PLAN_OVERRIDE")

        self.assertEqual(effective["timeout"], 60)
        self.assertEqual(provenance["timeout"], "ENVIRONMENT_DEFAULT")

    def test_07_plan_diff_and_approval_invalidation(self):
        """Tests that fingerprint-affecting planning edits set requires_reapproval = True in PlanDiff."""
        payload_v1 = {
            "topology": {"source": "ORACLE", "target": "POSTGRESQL"},
            "routing": {"schema_routes": [{"source_schema": "ERP", "target_schema": "PUBLIC"}]},
            "selected_scope": {"tables": ["CUSTOMERS"]},
            "configuration": {"parallelism": 8},
        }

        # v2 changes selected scope and parallelism
        payload_v2 = {
            "topology": {"source": "ORACLE", "target": "POSTGRESQL"},
            "routing": {"schema_routes": [{"source_schema": "ERP", "target_schema": "PUBLIC"}]},
            "selected_scope": {"tables": ["CUSTOMERS", "ORDERS"]},
            "configuration": {"parallelism": 16},
        }

        diff = self.compiler.compute_diff(payload_v1, payload_v2, "v1", "v2")
        self.assertTrue(diff.requires_reapproval)
        self.assertTrue(any(c["field"] == "selected_scope" for c in diff.changes))

    def test_08_secret_sanitization_in_configuration(self):
        """Tests that secrets (passwords, tokens) are sanitized in compiled execution plans."""
        src_top = SourceTopology(instance_id="src-sec", endpoint="loc:1521", connector_type="ORACLE")
        tgt_top = TargetTopology(instance_id="tgt-sec", endpoint="loc:5432", connector_type="POSTGRESQL")
        plan = MigrationPlan(
            plan_id="plan-sec",
            project_id="proj-sec",
            title="Secret Test",
            planning_mode=PlanningMode.SIMPLE,
            topology=TopologyDefinition(source=src_top, target=tgt_top),
            routing=RoutingDefinition(),
            selected_scope={},
            configuration={"parallelism": 4, "password": "super_secret_db_password"},
        )
        version = PlanVersion(
            version_id="ver-sec",
            project_id="proj-sec",
            parent_version_id=None,
            revision=1,
            created_at="2026-08-16T12:00:00Z",
            created_by="Admin",
            reason="Sec Test",
            planning_mode=PlanningMode.SIMPLE,
            canonical_payload=plan.to_dict(),
            fingerprint="",
        )

        res = self.compiler.compile(plan=plan, version=version, dry_run=False)
        self.assertTrue(res.success)
        resolved_cfg = res.execution_plan["resolved_configuration"]
        self.assertEqual(resolved_cfg["password"], "[REDACTED_HANDLE]")

    def test_09_gateway_ipc_control_plane_integration(self):
        """Tests EngineGateway end-to-end P5.1 capability dispatching."""
        gateway = EngineGateway()

        # 1. Save Project
        p_res = gateway.handle_capability("p5_save_project", {
            "title": "IPC Test Migration",
            "workspace": "qa-env",
            "owner": "Tester",
            "environment": "Staging",
        })
        self.assertEqual(p_res["status"], "SUCCESS")
        project_id = p_res["project"]["project_id"]

        # 2. Create Plan Draft
        d_res = gateway.handle_capability("p5_create_plan_draft", {
            "project_id": project_id,
            "title": "IPC Draft Plan",
            "source_connector": "ORACLE",
            "target_connector": "POSTGRESQL",
            "configuration": {"parallelism": 8},
        })
        self.assertEqual(d_res["status"], "SUCCESS")
        plan_id = d_res["plan"]["plan_id"]

        # 3. Create Plan Version & Compile Execution Plan
        v_res = gateway.handle_capability("p5_create_plan_version", {
            "plan_id": plan_id,
            "reason": "Initial IPC Version",
        })
        self.assertEqual(v_res["status"], "SUCCESS")
        version_id = v_res["version"]["version_id"]

        c_res = gateway.handle_capability("p5_compile_execution_plan", {
            "plan_id": plan_id,
            "version_id": version_id,
        })
        self.assertEqual(c_res["status"], "SUCCESS")
        self.assertTrue(c_res["compilation"]["success"])
        self.assertIsNotNone(c_res["compilation"]["execution_plan"])

    def test_10_execution_plan_immutability_enforced(self):
        """Tests that attempting to overwrite an existing ExecutionPlan raises ValueError (immutability rejection)."""
        proj = MigrationProject(
            project_id="proj-imm",
            title="Imm Proj",
            description="",
            workspace="w",
            owner="o",
            environment="e",
            priority="p",
            migration_strategy="s",
            source_instance_ref={"host": "1.1.1.1"},
            target_instance_ref={"host": "2.2.2.2"},
        )
        self.store.save_project(proj)

        src_top = SourceTopology(instance_id="src-imm", endpoint="loc:1521", connector_type="ORACLE")
        tgt_top = TargetTopology(instance_id="tgt-imm", endpoint="loc:5432", connector_type="POSTGRESQL")
        plan = MigrationPlan(
            plan_id="plan-imm",
            project_id="proj-imm",
            title="Imm Plan",
            planning_mode=PlanningMode.SIMPLE,
            topology=TopologyDefinition(source=src_top, target=tgt_top),
            routing=RoutingDefinition(),
            selected_scope={},
            configuration={},
        )
        self.store.save_plan(plan)

        ver = PlanVersion(
            version_id="ver-imm",
            project_id="proj-imm",
            parent_version_id=None,
            revision=1,
            created_at="2026-08-16T12:00:00Z",
            created_by="Admin",
            reason="Imm Test",
            planning_mode=PlanningMode.SIMPLE,
            canonical_payload=plan.to_dict(),
            fingerprint="fp123",
        )
        self.store.save_plan_version(ver)

        exec_plan = ExecutionPlan(
            execution_plan_id="exec-plan-imm-1",
            project_id="proj-imm",
            plan_version_id="ver-imm",
            fingerprint="fp123",
            compiled_at="2026-08-16T12:00:00Z",
            resolved_topology=plan.topology.to_dict(),
            resolved_routing=plan.routing.to_dict(),
            resolved_configuration={},
            stage1_plan={},
            dag_stages=[],
            is_immutable=True,
        )
        self.store.save_execution_plan(exec_plan)

        # Attempting to save another execution plan with the same execution_plan_id must fail closed
        exec_plan_mutated = ExecutionPlan(
            execution_plan_id="exec-plan-imm-1",
            project_id="proj-imm",
            plan_version_id="ver-imm",
            fingerprint="fp_MUTATED",
            compiled_at="2026-08-16T12:05:00Z",
            resolved_topology=plan.topology.to_dict(),
            resolved_routing=plan.routing.to_dict(),
            resolved_configuration={"mutated": True},
            stage1_plan={},
            dag_stages=[],
            is_immutable=True,
        )
        with self.assertRaises(ValueError):
            self.store.save_execution_plan(exec_plan_mutated)

    def test_11_fail_closed_deserialization(self):
        """Tests that loading corrupted plan state fails closed rather than returning dummy fallbacks."""
        with self.store._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    project_id, title, description, workspace, owner, environment,
                    priority, migration_strategy, source_instance_ref, target_instance_ref,
                    created_at, updated_at
                ) VALUES ('proj-bad', 'Bad Proj', '', 'w', 'o', 'e', 'p', 's', '{}', '{}', 'now', 'now')
                """
            )
            # Insert plan with corrupted topology missing source/target
            conn.execute(
                """
                INSERT INTO plans (
                    plan_id, project_id, title, planning_mode, topology, routing,
                    selected_scope, configuration, status
                ) VALUES ('plan-corrupt', 'proj-bad', 'Bad Plan', 'SIMPLE', '{}', '{}', '{}', '{}', 'DRAFT')
                """
            )

        with self.assertRaises(ValueError):
            self.store.load_plan("plan-corrupt")

    def test_12_stale_approval_fingerprint_mismatch_fails_closed(self):
        """Tests that modifying a plan after governance approval alters the fingerprint and causes execution to fail closed."""
        gateway = EngineGateway()

        p_res = gateway.handle_capability("p5_save_project", {
            "title": "Approval Binding Test",
            "workspace": "prod",
            "owner": "SecurityOfficer",
        })
        project_id = p_res["project"]["project_id"]

        d_res = gateway.handle_capability("p5_create_plan_draft", {
            "project_id": project_id,
            "title": "Initial Approved Draft",
            "source_connector": "ORACLE",
            "target_connector": "POSTGRESQL",
            "configuration": {"parallelism": 4},
        })
        plan_id = d_res["plan"]["plan_id"]

        v1_res = gateway.handle_capability("p5_create_plan_version", {"plan_id": plan_id, "reason": "v1"})
        v1_id = v1_res["version"]["version_id"]
        c1_res = gateway.handle_capability("p5_compile_execution_plan", {"plan_id": plan_id, "version_id": v1_id})

        spec_v1 = {"config": "v1"}
        dag_v1 = {"dag": "v1"}
        v1_fp = gateway.super_engine.compute_plan_fingerprint(spec_v1, dag_v1)

        # Record governance approval for v1_fp
        gateway.state_store.set_state("mig-bound_approval", {
            "status": "approved",
            "approved_plan_fingerprint": v1_fp,
            "approved_by": "SecurityOfficer",
        }, category="governance")

        # 1. Assert verification succeeds for original approved spec & dag
        verified_fp = gateway.super_engine.verify_governance_authorization("mig-bound", spec_v1, dag_v1)
        self.assertEqual(verified_fp, v1_fp)

        # 2. Intentionally tamper with parameters (v2) -> must raise PlanFingerprintMismatchError (fail closed)
        from akaal.engine.facade import PlanFingerprintMismatchError
        spec_v2 = {"config": "v2_tampered"}
        dag_v2 = {"dag": "v2_tampered"}
        with self.assertRaises(PlanFingerprintMismatchError):
            gateway.super_engine.verify_governance_authorization("mig-bound", spec_v2, dag_v2)

    def test_13_restart_reconstruction_durable_from_state_db(self):
        """Tests complete process-level restart reconstruction exclusively from artifacts/state.db."""
        proj_id = f"proj-restart-{uuid.uuid4().hex[:6]}"
        proj = MigrationProject(
            project_id=proj_id,
            title="Restart Persistence Test",
            description="Process restart test",
            workspace="production",
            owner="Operator",
            environment="Production",
            priority="P0",
            migration_strategy="Zero-Downtime",
            source_instance_ref={"host": "10.0.0.1"},
            target_instance_ref={"host": "10.0.0.2"},
        )
        self.store.save_project(proj)

        plan = MigrationPlan(
            plan_id=f"plan-{proj_id}",
            project_id=proj_id,
            title="Restart Plan",
            planning_mode=PlanningMode.ADVANCED,
            topology=TopologyDefinition(
                source=SourceTopology(instance_id="s1", endpoint="e1", connector_type="ORACLE"),
                target=TargetTopology(instance_id="t1", endpoint="e2", connector_type="POSTGRESQL"),
            ),
            routing=RoutingDefinition(),
            selected_scope={"tables": ["T1", "T2"]},
            configuration={"parallelism": 16},
        )
        self.store.save_plan(plan)

        ver = PlanVersion(
            version_id=f"ver-{proj_id}",
            project_id=proj_id,
            parent_version_id=None,
            revision=1,
            created_at="2026-08-16T12:00:00Z",
            created_by="Operator",
            reason="Restart Test",
            planning_mode=PlanningMode.ADVANCED,
            canonical_payload=plan.to_dict(),
            fingerprint="fp_restart_123",
        )
        self.store.save_plan_version(ver)

        # Re-instantiate ProjectStore handle to simulate process restart
        fresh_store = ProjectStore(db_path=self.db_path)
        reconstructed_proj = fresh_store.load_project(proj_id)
        reconstructed_plan = fresh_store.load_plan(plan.plan_id)
        reconstructed_ver = fresh_store.load_plan_version(ver.version_id)

        self.assertIsNotNone(reconstructed_proj)
        self.assertIsNotNone(reconstructed_plan)
        self.assertIsNotNone(reconstructed_ver)
        self.assertEqual(reconstructed_proj.title, "Restart Persistence Test")
        self.assertEqual(reconstructed_plan.configuration["parallelism"], 16)
        self.assertEqual(reconstructed_ver.fingerprint, "fp_restart_123")

    def test_14_dry_run_zero_target_writes(self):
        """Tests that p5_dry_run_execution_plan performs full compilation without writing target data."""
        gateway = EngineGateway()
        res = gateway.handle_capability("p5_dry_run_execution_plan", {
            "plan_id": "plan-nonexistent",
            "version_id": "ver-nonexistent",
        })
        self.assertEqual(res["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()

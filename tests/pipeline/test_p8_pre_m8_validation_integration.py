"""
tests/pipeline/test_p8_pre_m8_validation_integration.py
==========================================================
Focused Integration Tests for DevKros Pre-M8 Validation Studio Blocker Closure:
- Blocker 1: Step 4 comparison_units & Step 6 assurance_exceptions payload survival in SQLite DB.
- Blocker 2: Level-5 ExactRowReconciler DisputedRecord persistence & query projection.
"""

import json
import sqlite3
import tempfile
import unittest
from typing import Any, Dict

from akaalEngine.validation.api import ValidationAuthority
from akaalEngine.validation.models.plan import ValidationMode, ValidationPlan
from akaalEngine.validation.models.result import DisputedRecord, ValidationResult
from akaalPipeline.contracts.enums import AuthenticationAssurance, AuthenticationState
from akaalPipeline.contracts.errors import PipelineError
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalPipeline.validation.models import ValidationMissionRecord, ValidationMissionState
from akaalPipeline.validation.service import ValidationPipelineService


class TestPreM8ValidationIntegrationBlockerClosure(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp_db.name
        self.uow = SQLiteUnitOfWork(db_path=self.db_path)
        with self.uow as uow:
            uow.connection.commit()

        self.service = ValidationPipelineService()
        self.actor = PipelineActorContext(
            actor_id="test-operator-1",
            actor_type="HUMAN",
            organization_id="default-tenant",
            workspace_id="default-workspace",
            project_id="proj-p8-test",
            roles=("MIGRATION_OPERATOR", "MIGRATION_ADMIN"),
            authentication_state=AuthenticationState.AUTHENTICATED,
            authentication_assurance=AuthenticationAssurance.MEDIUM,
        )

    # =========================================================================
    # BLOCKER 1 TESTS — WIZARD PAYLOAD SERIALIZATION & SURVIVAL
    # =========================================================================

    def test_w1_w2_w3_w4_wizard_payload_survival_in_sqlite(self) -> None:
        """Verifies Step 4 comparison_units and Step 6 assurance_exceptions survive in SQLite."""
        scope_units = [
            {
                "unitId": "unit-1",
                "sourceName": "CUSTOMERS",
                "expectedTargetName": "CUSTOMERS_TGT",
                "disposition": "INCLUDED",
                "targetStatus": "CONFIRMED",
                "columnMapping": {"CUST_ID": "ID", "CUST_NAME": "NAME"},
            },
            {
                "unitId": "unit-2",
                "sourceName": "ORDERS",
                "expectedTargetName": "ORDERS_TGT",
                "disposition": "INCLUDED",
                "targetStatus": "CONFIRMED",
            },
        ]

        assurance_exceptions = [
            {
                "groupId": "ex-1",
                "reason": "Legacy timestamp precision loss tolerance",
                "targetAssuranceLevel": "CARDINALITY",
                "objectIds": ["CUSTOMERS.CREATED_AT"],
            }
        ]

        payload = {
            "name": "Mission Alpha with Full Scope",
            "source_provider": "Oracle",
            "target_provider": "PostgreSQL",
            "temporal_strategy": "EXECUTE_ON_INIT",
            "environment": "Production",
            "project_id": "proj-p8-test",
            "scope_config": {
                "table_name": "CUSTOMERS",
                "comparison_units": scope_units,
                "selected_correspondence_rule": "EXACT_IDENTIFIER_MATCH",
                "step4_pathway": "DEFINE",
            },
            "execution_policy": {
                "mode": "PARTITION_FINGERPRINT",
                "temporal_cadence": "CONSISTENT_STATE",
                "coverage_policy": "EXHAUSTIVE",
                "assurance_exceptions": assurance_exceptions,
            },
        }

        with self.uow as uow:
            mission = self.service.create_mission(payload, self.actor, uow.connection)

        self.assertIsNotNone(mission.mission_id)
        self.assertEqual(mission.name, "Mission Alpha with Full Scope")

        # Query mission back from SQLite
        with self.uow as uow:
            retrieved = self.service.get_mission(mission.mission_id, self.actor, uow.connection)

        # Assert Step 4 Comparison Units survival
        self.assertIn("comparison_units", retrieved.scope_config)
        units = retrieved.scope_config["comparison_units"]
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0]["sourceName"], "CUSTOMERS")
        self.assertEqual(units[1]["sourceName"], "ORDERS")

        # Assert Step 6 Assurance Exceptions survival
        self.assertIn("assurance_exceptions", retrieved.execution_policy)
        exceptions = retrieved.execution_policy["assurance_exceptions"]
        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0]["groupId"], "ex-1")
        self.assertEqual(exceptions[0]["targetAssuranceLevel"], "CARDINALITY")

    def test_w5_step5_boundary_baseline_regression_check(self) -> None:
        """Verifies Step 5 maintenance baseline creation works with no regression."""
        payload = {
            "name": "Baseline Mission",
            "source_provider": "PostgreSQL",
            "target_provider": "MariaDB",
            "baseline_intent": "MAINTENANCE_COORDINATED",
            "maintenance_condition": "WRITES_STOPPED_DECLARED",
        }
        with self.uow as uow:
            mission = self.service.create_mission(payload, self.actor, uow.connection)

        self.assertIsNotNone(mission.baseline_id)
        with self.uow as uow:
            base = self.service.boundary_manager.get_baseline(mission.baseline_id, uow.connection)
        self.assertIsNotNone(base)
        self.assertEqual(base.condition_type, "WRITES_STOPPED_DECLARED")

    # =========================================================================
    # BLOCKER 2 TESTS — DISCREPANCY PERSISTENCE & QUERY PROJECTION
    # =========================================================================

    def test_d1_d2_d3_d4_discrepancy_persistence_and_query(self) -> None:
        """Verifies Level-5 ExactRowReconciler DisputedRecords persist to SQLite and query via IPC."""
        payload = {
            "name": "Mission Beta for Discrepancy Persistence",
            "source_provider": "Oracle",
            "target_provider": "PostgreSQL",
            "scope_config": {"table_name": "ACCOUNTS"},
        }

        with self.uow as uow:
            mission = self.service.create_mission(payload, self.actor, uow.connection)

        # Mismatched row payload
        source_rows = [
            {"id": 101, "name": "Alice", "balance": 1000},
            {"id": 102, "name": "Bob", "balance": 5000},
            {"id": 103, "name": "Charlie", "balance": 250},
        ]
        target_rows = [
            {"id": 101, "name": "Alice", "balance": 1000},
            {"id": 102, "name": "Bob", "balance": 4999},  # Mismatch on balance
            # 103 is missing on target
        ]

        with self.uow as uow:
            res = self.service.execute_mission_immediately(
                mission_id=mission.mission_id,
                actor=self.actor,
                conn=uow.connection,
                source_rows=source_rows,
                target_rows=target_rows,
                pk_columns=["id"],
            )

        self.assertEqual(res["status"], "MISMATCH")
        val_result = res["validation_result"]
        self.assertGreater(val_result["rows_mismatched"] + val_result["rows_missing"], 0)

        # Query discrepancies back from SQLite
        with self.uow as uow:
            discrepancies = self.service.list_discrepancies(
                mission_id=mission.mission_id,
                actor=self.actor,
                conn=uow.connection,
            )

        self.assertGreaterEqual(len(discrepancies), 1)
        first_disc = discrepancies[0]
        self.assertEqual(first_disc["mission_id"], mission.mission_id)
        self.assertEqual(first_disc["table_name"], "ACCOUNTS")
        self.assertEqual(first_disc["status"], "UNRESOLVED")

        # Query single discrepancy detail
        with self.uow as uow:
            detail = self.service.get_discrepancy_detail(
                discrepancy_id=first_disc["discrepancy_id"],
                actor=self.actor,
                conn=uow.connection,
            )

        self.assertEqual(detail["discrepancy_id"], first_disc["discrepancy_id"])
        self.assertIsNotNone(detail["source_value"])

    def test_d7_zero_discrepancy_run_returns_empty_list(self) -> None:
        """Verifies a 100% matching validation run stores 0 discrepancies and returns an empty list."""
        payload = {
            "name": "Mission Gamma Perfect Pass",
            "source_provider": "PostgreSQL",
            "target_provider": "MariaDB",
        }

        with self.uow as uow:
            mission = self.service.create_mission(payload, self.actor, uow.connection)

        matching_rows = [{"id": 1, "val": "OK"}, {"id": 2, "val": "OK"}]
        with self.uow as uow:
            res = self.service.execute_mission_immediately(
                mission_id=mission.mission_id,
                actor=self.actor,
                conn=uow.connection,
                source_rows=matching_rows,
                target_rows=matching_rows,
                pk_columns=["id"],
            )

        self.assertEqual(res["status"], "SUCCESS")

        with self.uow as uow:
            discrepancies = self.service.list_discrepancies(
                mission_id=mission.mission_id,
                actor=self.actor,
                conn=uow.connection,
            )

        self.assertEqual(len(discrepancies), 0)

    def test_d8_d12_unexecuted_mission_scope_isolation(self) -> None:
        """Verifies unauthorized scope access is rejected and unexecuted mission returns empty list."""
        payload = {
            "name": "Mission Delta Unexecuted",
            "source_provider": "Oracle",
            "target_provider": "PostgreSQL",
        }
        with self.uow as uow:
            mission = self.service.create_mission(payload, self.actor, uow.connection)

        with self.uow as uow:
            discrepancies = self.service.list_discrepancies(
                mission_id=mission.mission_id,
                actor=self.actor,
                conn=uow.connection,
            )
        self.assertEqual(len(discrepancies), 0)

        # Cross-tenant actor attempting to access mission discrepancies
        unauthorized_actor = PipelineActorContext(
            actor_id="hacker-1",
            actor_type="HUMAN",
            organization_id="unauthorized-tenant-99",
            workspace_id="unauthorized-workspace",
            roles=("MIGRATION_OPERATOR",),
            authentication_state=AuthenticationState.AUTHENTICATED,
            authentication_assurance=AuthenticationAssurance.MEDIUM,
        )

        with self.assertRaises(PipelineError):
            with self.uow as uow:
                self.service.list_discrepancies(
                    mission_id=mission.mission_id,
                    actor=unauthorized_actor,
                    conn=uow.connection,
                )


if __name__ == "__main__":
    unittest.main()

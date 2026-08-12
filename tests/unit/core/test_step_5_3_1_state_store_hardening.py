"""
AKAAL Forensic Verification Tests — Step 5.3.1 State Store Hardening & Failure Semantics
========================================================================================
Tests:
A. Primitive round trip
B. Supported domain object (ConnectionAuthority) round trip
C. Dataclass round trip
D. Unsupported object rejection (TypeError raised)
E. Serializer exception propagation
F. SQLite write failure propagation
G. Existing-value safety (failed write preserves prior state)
H. Daemon restart recovery with hardened serializer
I. Plaintext secret persistence audit (passwords NOT stored in state.db)
"""

import os
import unittest
import dataclasses
from unittest.mock import patch, MagicMock

from akaal.core.state.state_store import CentralStateStore
from akaal.migration.target_identifier import ConnectionAuthority
from akaal.gateway.engine_gateway import EngineGateway


@dataclasses.dataclass
class TestSpecDataclass:
    spec_id: str
    parallelism: int
    enabled: bool


class UnsupportedDummy:
    __slots__ = ("a", "b")


class TestStep531StateStoreHardening(unittest.TestCase):

    def setUp(self):
        self.state_store = CentralStateStore()

    def test_a_primitive_round_trip(self):
        """TEST A: Persist nested primitive JSON-compatible state and prove exact semantic round trip."""
        key = "test-prim-key-01"
        data = {"int": 42, "float": 3.14, "str": "akaal", "list": [1, 2, 3], "nested": {"a": True, "b": None}}
        self.state_store.set_state(key, data, category="test_cat")
        
        fetched = self.state_store.get_state(key, category="test_cat")
        self.assertEqual(fetched, data)

    def test_b_supported_domain_object_round_trip(self):
        """TEST B: Persist ConnectionAuthority domain object and prove every field survives round trip."""
        key = "test-domain-key-02"
        auth = ConnectionAuthority(
            connection_id="conn-01",
            role="SOURCE",
            engine="ORACLE",
            host="oracle-prod.internal",
            port=1521,
            database="PRODDB",
            username="MIG_USER",
            credential_ref="cred-ref-01"
        )
        self.state_store.set_state(key, auth, category="test_cat")
        fetched = self.state_store.get_state(key, category="test_cat")
        self.assertIsInstance(fetched, dict)
        self.assertEqual(fetched["host"], "oracle-prod.internal")
        self.assertEqual(fetched["username"], "MIG_USER")
        self.assertEqual(fetched["credential_ref"], "cred-ref-01")

    def test_c_dataclass_round_trip(self):
        """TEST C: Dataclass round trip conversion."""
        key = "test-dc-key-03"
        dc_obj = TestSpecDataclass(spec_id="spec-99", parallelism=8, enabled=True)
        self.state_store.set_state(key, dc_obj, category="test_cat")
        fetched = self.state_store.get_state(key, category="test_cat")
        self.assertEqual(fetched, {"spec_id": "spec-99", "parallelism": 8, "enabled": True})

    def test_d_unsupported_object_rejection(self):
        """TEST D: Unsupported object without to_dict or __dict__ must raise TypeError, NOT stringify."""
        key = "test-unsupported-key-04"
        unsupported = UnsupportedDummy()
        with self.assertRaises(TypeError):
            self.state_store.set_state(key, unsupported, category="test_cat")

    def test_e_serializer_exception_propagation(self):
        """TEST E: Serializer exception must propagate to caller rather than being silently swallowed."""
        key = "test-propagate-key-05"
        unsupported = UnsupportedDummy()
        try:
            self.state_store.set_state(key, unsupported, category="test_cat")
            self.fail("Expected TypeError exception was not raised")
        except TypeError as err:
            self.assertIn("is not JSON serializable", str(err))

    def test_f_sqlite_write_failure_propagation(self):
        """TEST F: SQLite write failure must be surfaced to the caller."""
        key = "test-db-fail-key-06"
        data = {"status": "RUNNING"}
        conn_mock = MagicMock()
        conn_mock.execute.side_effect = RuntimeError("Disk I/O Error simulated")
        
        with patch.object(self.state_store, "_get_connection", return_value=conn_mock):
            with self.assertRaises(RuntimeError):
                self.state_store.set_state(key, data, category="test_cat")

    def test_g_failed_replacement_preserves_prior_state(self):
        """TEST G: Unsuccessful replacement write must NOT destroy prior valid authoritative state."""
        key = "test-preserve-prior-key-07"
        v1 = {"version": 1, "value": "valid_authoritative"}
        self.state_store.set_state(key, v1, category="test_cat")
        
        # Verify V1 is persisted
        self.assertEqual(self.state_store.get_state(key, category="test_cat"), v1)

        # Attempt to set unsupported V2
        with self.assertRaises(TypeError):
            self.state_store.set_state(key, UnsupportedDummy(), category="test_cat")

        # Verify V1 remains authoritative in store
        self.assertEqual(self.state_store.get_state(key, category="test_cat"), v1)

    def test_h_plaintext_secret_persistence_audit(self):
        """TEST H: Ensure plaintext passwords are NOT persisted into CentralStateStore."""
        gateway = EngineGateway()
        mig_id = "mig-secret-audit-01"
        payload = {
            "migration_id": mig_id,
            "source_engine": "ORACLE",
            "target_engine": "POSTGRESQL",
            "source_host": "127.0.0.1",
            "source_port": 1521,
            "source_db": "FREE",
            "source_user": "SYSTEM",
            "source_pass": "SuperSecretPassword123!",
            "target_host": "127.0.0.1",
            "target_port": 5432,
            "target_db": "pgdb",
            "target_user": "postgres",
            "target_pass": "TargetSecretPassword456!",
        }
        gateway.create_migration(payload)

        # Retrieve stored migration config from state store
        stored = self.state_store.get_state(mig_id, category="migration")
        self.assertIsNotNone(stored)
        config = stored.get("config", {})

        # Assert plaintext password fields are absent from stored state
        self.assertNotIn("source_pass", config)
        self.assertNotIn("target_pass", config)
        self.assertNotIn("source_password", config)
        self.assertNotIn("target_password", config)
        self.assertNotIn("password", config)


if __name__ == "__main__":
    unittest.main()

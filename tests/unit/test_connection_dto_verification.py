"""
AKAAL Connection DTO Verification Unit Test Suite
=================================================
Verifies canonical connection DTO structures for Oracle and PostgreSQL
under valid, invalid, and privileged (SYSDBA / NORMAL) scenarios.
"""

import unittest
from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.credential_vault import credential_vault
from tests.conftest import require_oracle, require_postgres


class TestConnectionDTOVerification(unittest.TestCase):


    def setUp(self):
        self.gateway = EngineGateway()

    def test_credential_vault_diagnostic_and_canonical_contract(self):
        """Verify CredentialVault exposes canonical store_credentials and alias set_credentials."""
        ref = credential_vault.store_credentials({"password": "secret_pass_123"})
        self.assertTrue(ref.startswith("cred-ref-"))
        resolved = credential_vault.get_credentials(ref)
        self.assertEqual(resolved["password"], "secret_pass_123")

        # Test set_credentials alias method
        ref_alias = credential_vault.set_credentials("cred-ref-alias-test", {"password": "alias_pass_456"})
        self.assertEqual(ref_alias, "cred-ref-alias-test")
        self.assertEqual(credential_vault.get_credentials("cred-ref-alias-test")["password"], "alias_pass_456")

    def test_oracle_normal_user_connects(self):
        require_oracle("localhost", 1521)
        payload = {
            "system_type": "Oracle 19c",
            "host": "localhost",
            "port": 1521,
            "database_name": "instance2_pdb",
            "username": "SYSTEM",
            "password": "aalok",
            "privilege_mode": "NORMAL"
        }
        res = self.gateway.test_connection(payload)
        self.assertTrue(res["connected"])
        self.assertEqual(res["privilege_mode"], "NORMAL")

    def test_oracle_sys_sysdba_connects(self):
        require_oracle("localhost", 1521)
        payload = {
            "system_type": "Oracle 19c",
            "host": "localhost",
            "port": 1521,
            "database_name": "instance2_pdb",
            "username": "sys",
            "password": "aalok",
            "privilege_mode": "SYSDBA"
        }
        res = self.gateway.test_connection(payload)
        self.assertTrue(res["connected"])
        self.assertEqual(res["privilege_mode"], "SYSDBA")

    def test_oracle_sys_normal_mode_surfaces_error(self):
        require_oracle("localhost", 1521)
        payload = {
            "system_type": "Oracle 19c",
            "host": "localhost",
            "port": 1521,
            "database_name": "instance2_pdb",
            "username": "sys",
            "password": "aalok",
            "privilege_mode": "NORMAL"
        }
        res = self.gateway.test_connection(payload)
        self.assertFalse(res["connected"])
        self.assertIn("ORA-", res["message"])

    def test_oracle_invalid_password_surfaces_sanitized_error(self):
        require_oracle("localhost", 1521)
        payload = {
            "system_type": "Oracle 19c",
            "host": "localhost",
            "port": 1521,
            "database_name": "instance2_pdb",
            "username": "SYSTEM",
            "password": "WRONG_SYSTEM_PASSWORD",
            "privilege_mode": "NORMAL"
        }
        res = self.gateway.test_connection(payload)
        self.assertFalse(res["connected"])
        self.assertIn("ORA-01017", res["message"])

    def test_postgresql_valid_credentials_unaffected(self):
        require_postgres("127.0.0.1", 5432)
        payload = {
            "system_type": "PostgreSQL 16",
            "host": "127.0.0.1",
            "port": 5432,
            "database_name": "postgres",
            "username": "postgres",
            "password": "postgres",
            "privilege_mode": "NORMAL"
        }
        res = self.gateway.test_connection(payload)
        if not res["connected"]:
            payload["port"] = 5433
            res = self.gateway.test_connection(payload)
        self.assertTrue(res["connected"])
        self.assertEqual(res["system_type"], "POSTGRESQL 16")



if __name__ == "__main__":
    unittest.main()

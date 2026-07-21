"""
Unit Tests for AKAAL Platform Part 6 - Security, Governance & Compliance Subsystems.
"""

import unittest
from akaal.platform.security.enterprise_security_manager import EnterpriseSecurityManager
from akaal.platform.governance.governance_manager import GovernanceManager
from akaal.platform.compliance.compliance_manager import ComplianceManager
from akaal.platform.configuration.configuration_manager import ConfigurationManager


class TestSecurityGovernanceCompliance(unittest.TestCase):

    def setUp(self):
        self.sec = EnterpriseSecurityManager()
        self.gov = GovernanceManager()
        self.comp = ComplianceManager()
        self.cfg = ConfigurationManager()

    def test_cryptographic_audit_log_chain_integrity(self):
        rec1 = self.sec.audit("admin-1", "DEPLOY_TOPOLOGY", "top-101")
        rec2 = self.sec.audit("admin-1", "SCALE_WORKER_POOL", "node-5")
        rec3 = self.sec.audit("system", "ROTATE_TLS_CERTS", "tls-context")

        self.assertEqual(rec2.prev_hash, rec1.record_hash)
        self.assertEqual(rec3.prev_hash, rec2.record_hash)
        self.assertTrue(self.sec.audit_logging.verify_chain_integrity())

    def test_key_rotation_and_envelope_encryption(self):
        v1_key = self.sec.key_management._current_key_version
        enc = self.sec.key_management.encrypt_secret("db-password-secret")
        self.assertIn(f"ENC:v{v1_key}:", enc)

        v2_key = self.sec.key_management.rotate_master_key()
        self.assertEqual(v2_key, v1_key + 1)

    def test_dynamic_configuration_and_feature_flags(self):
        self.cfg.set_config("akaal.buffer.pool_size_mb", 2048)
        self.assertEqual(self.cfg.get_config("akaal.buffer.pool_size_mb"), 2048)

        self.assertFalse(self.cfg.feature_flags.is_enabled("zero_copy_rdma"))
        self.cfg.feature_flags.enable_feature("zero_copy_rdma")
        self.assertTrue(self.cfg.feature_flags.is_enabled("zero_copy_rdma"))

    def test_regulatory_compliance_audit(self):
        soc2 = self.comp.audit_standard("SOC2")
        self.assertTrue(soc2.compliant)
        self.assertEqual(soc2.passed_controls_count, 42)

        gdpr = self.comp.audit_standard("GDPR")
        self.assertTrue(gdpr.compliant)


if __name__ == "__main__":
    unittest.main()

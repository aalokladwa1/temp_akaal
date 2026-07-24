"""
AKAAL Platform 11 — Enterprise Trust & Certification Unit & Integration Test Suite.
Verifies all 6 capabilities: Immutable Ledger, Trust Score, Certification Report, Evidence Package, Digital Seal, Audit Export.
"""

import unittest
import asyncio

from akaal.trust_certification import EnterpriseTrustCertificationPlatformV11
from akaal.api.facades.platform11 import Platform11Facade


class TestPlatform11TrustCertification(unittest.TestCase):

    def setUp(self):
        self.platform = EnterpriseTrustCertificationPlatformV11()
        self.facade = Platform11Facade(self.platform)

    def test_capabilities_dto(self):
        caps = asyncio.run(self.facade.get_capabilities())
        self.assertEqual(caps.platform_name, "Platform 11 (Enterprise Trust & Certification Platform)")
        self.assertEqual(len(caps.supported_features), 6)

    def test_immutable_ledger_hash_chain(self):
        entry1 = self.platform.record_validation({"step": 1, "status": "OK"})
        entry2 = self.platform.record_validation({"step": 2, "status": "OK"})
        self.assertEqual(entry2.previous_hash, entry1.block_hash)
        self.assertTrue(self.platform.validation_ledger.verify_chain())

    def test_migration_trust_score(self):
        score = self.platform.compute_trust_score("mig-cert-100", 100.0, 100.0)
        self.assertEqual(score.trust_score, 100.0)
        self.assertEqual(score.grade.value, "GRADE_AAA")

    def test_certification_report(self):
        score = self.platform.compute_trust_score("mig-cert-100", 100.0, 100.0)
        cert = self.platform.generate_certificate(score)
        self.assertEqual(cert.grade.value, "GRADE_AAA")

    def test_compliance_evidence(self):
        ev = self.platform.assemble_evidence("mig-cert-100", [{"rule": "SCHEMA_MATCH", "result": "PASS"}])
        self.assertEqual(ev.target_migration_id, "mig-cert-100")

    def test_digital_certification_seal(self):
        seal = self.platform.issue_seal("mig-cert-100", 100.0)
        self.assertEqual(seal.status.value, "VALID")

    def test_audit_export(self):
        exp = self.platform.export_audit("mig-cert-100")
        self.assertEqual(exp.archive_format, "ZIP_JSON")

    def test_facade_async_validation_record(self):
        res = asyncio.run(self.facade.record_validation({"test": "facade"}))
        self.assertIn("block_hash", res)


if __name__ == "__main__":
    unittest.main()

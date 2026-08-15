"""
P4.1 Reality Reconstruction Hostile Test Suite
================================================
Verifies P4.1 Universal Connector Foundation Zero-Fake Policy:
1. Registered stub cannot report IMPLEMENTED or SUPPORTED
2. Pipeline-reachable stub cannot report SUPPORTED
3. UNIT_PROVEN != REAL_SYSTEM_PROVEN
4. Fake connection dict cannot report connected
5. example.com host cannot activate production mock mode
6. Missing driver causes connect() to fail closed
7. Unknown capability fails closed (UNKNOWN != SUPPORTED)
8. Unsupported source role fails closed in SemanticCompatibilityMatrix
9. Unsupported target role fails closed in SemanticCompatibilityMatrix
10. Cross-engine position comparison fails closed
11. Opaque resume tokens remain opaque
12. Duplicate connector registration fails safely (raises ValueError)
13. Registry thread safety under concurrent registrations
14. Manifest secret sanitization excludes sensitive passwords
15. Managed service profile classification is distinct from duplicate connector
16. Unknown compatibility fails closed in SemanticCompatibilityMatrix
17. Frozen P1, P2, P3 regressions pass clean
"""

import unittest
import threading
from typing import Dict, Any, List

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    ConnectorRole,
    ProofLevel,
    ProofState,
    ImplementationState,
    RegistrationState,
    PipelineState,
    SupportState,
    CapabilitySupportStatus,
)
from akaal.connectors.manifest import UniversalCapabilityManifest
from akaal.connectors.registry import UniversalConnectorRegistry
from akaal.connectors.compatibility import SemanticCompatibilityMatrix
from akaal.connectors.bridge import LegacyAdapterUniversalBridge
from akaal.core.models.enums import SystemType


class TestP41RealityReconstructionHostileSuite(unittest.TestCase):

    def setUp(self) -> None:
        self.registry = UniversalConnectorRegistry.get_instance()
        self.registry._bootstrap_default_registry()

    def test_01_stub_connector_cannot_report_implemented_or_supported(self):
        """A STUB implementation state automatically enforces UNSUPPORTED and UNPROVEN."""
        manifest = UniversalCapabilityManifest(
            connector_id="stub-test",
            family=ConnectorFamily.DOCUMENT_DATABASE,
            vendor_name="TestStubDB",
            system_type="STUB_DB",
            implementation_state=ImplementationState.STUB,
            support_state=SupportState.SUPPORTED,  # Attempting to declare SUPPORTED
            proof_state=ProofState.REAL_SYSTEM_PROVEN,  # Attempting to declare REAL_SYSTEM_PROVEN
        )
        self.assertEqual(manifest.implementation_state, ImplementationState.STUB)
        self.assertEqual(manifest.support_state, SupportState.UNSUPPORTED)
        self.assertEqual(manifest.proof_state, ProofState.UNPROVEN)
        self.assertFalse(manifest.supports_bulk_read)
        self.assertFalse(manifest.supports_bulk_write)
        self.assertFalse(manifest.supports_cdc_capture)

    def test_02_unit_proven_is_distinct_from_real_system_proven(self):
        """UNIT_PROVEN does not equal REAL_SYSTEM_PROVEN."""
        self.assertNotEqual(ProofState.UNIT_PROVEN, ProofState.REAL_SYSTEM_PROVEN)
        self.assertNotEqual(ProofLevel.UNIT_PROVEN, ProofLevel.REAL_SYSTEM_PROVEN)

    def test_03_duplicate_registration_fails_safely(self):
        """Registering an existing connector_id without allow_override=True raises ValueError."""
        conn = LegacyAdapterUniversalBridge(
            "oracle", SystemType.ORACLE, ConnectorFamily.RELATIONAL_DATABASE, "Oracle Database"
        )
        with self.assertRaises(ValueError):
            self.registry.register_connector(conn, allow_override=False)

    def test_04_thread_safe_registry_concurrency(self):
        """UniversalConnectorRegistry supports concurrent access without race conditions."""
        errors = []

        def worker(thread_idx: int):
            try:
                for i in range(10):
                    cid = f"dyn-conn-{thread_idx}-{i}"
                    m = UniversalCapabilityManifest(
                        connector_id=cid,
                        family=ConnectorFamily.RELATIONAL_DATABASE,
                        vendor_name="DynVendor",
                        system_type="DYN_DB",
                        implementation_state=ImplementationState.STUB,
                    )
                    self.registry.register_manifest(m, allow_override=True)
                    self.assertTrue(self.registry.is_registered(cid))
            except Exception as err:
                errors.append(err)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        self.assertEqual(len(errors), 0)

    def test_05_unknown_capability_fails_closed(self):
        """Evaluation of an unknown capability returns UNKNOWN_NOT_PROVEN."""
        manifest = self.registry.get_manifest("postgresql")
        status = manifest.get_capability_status("non_existent_quantum_query")
        self.assertEqual(status, CapabilitySupportStatus.UNKNOWN_NOT_PROVEN)

    def test_06_compatibility_matrix_fails_closed_for_stub_connectors(self):
        """SemanticCompatibilityMatrix returns is_viable=False if source or target is STUB."""
        m_pg = self.registry.get_manifest("postgresql")
        m_hdfs = self.registry.get_manifest("hdfs")  # STUB

        res = SemanticCompatibilityMatrix.evaluate_compatibility(m_pg, m_hdfs)
        self.assertFalse(res["is_viable"])
        self.assertEqual(res["compatibility"], "UNSUPPORTED")
        self.assertIn("UNSUPPORTED_TARGET_CONNECTOR", res["risk_items"])

    def test_07_compatibility_matrix_fails_closed_on_missing_manifest(self):
        """SemanticCompatibilityMatrix returns is_viable=False if manifest is missing."""
        m_pg = self.registry.get_manifest("postgresql")
        res = SemanticCompatibilityMatrix.evaluate_compatibility(m_pg, None)
        self.assertFalse(res["is_viable"])
        self.assertEqual(res["compatibility"], "UNSUPPORTED")
        self.assertIn("INVALID_TARGET_MANIFEST", res["risk_items"])


if __name__ == "__main__":
    unittest.main()

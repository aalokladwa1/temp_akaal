"""
Integration Boundary & Architecture Isolation Verification Tests for Platform 9.
"""

import os
import glob
from akaal.operations.verification.architecture import ArchitectureVerifier


def test_platform9_boundary_isolation():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    operations_path = os.path.join(base_dir, "akaal", "operations")

    python_files = glob.glob(os.path.join(operations_path, "**", "*.py"), recursive=True)
    assert len(python_files) > 0, "No python source files found in akaal/operations."

    success, violations = ArchitectureVerifier.verify_boundaries(python_files)
    assert success is True, f"Platform 9 boundary violations detected: {violations}"

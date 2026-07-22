"""
Integration Boundary and Architecture Verification Tests.
"""

import os
import glob
from akaal.performance.verification.architecture import ArchitectureVerifier


def test_platform_boundary_isolation():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    performance_path = os.path.join(base_dir, "akaal", "performance")
    
    python_files = glob.glob(os.path.join(performance_path, "**", "*.py"), recursive=True)
    assert len(python_files) > 0, "No python source files found in performance directory."

    success, violations = ArchitectureVerifier.verify_boundaries(python_files)
    assert success is True, f"Platform boundary violations found: {violations}"

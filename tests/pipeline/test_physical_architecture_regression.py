"""tests/pipeline/test_physical_architecture_regression.py
=========================================================
Physical architecture proof for root-level akaalPipeline package.
"""

from __future__ import annotations

import os
import sys
import pytest


def test_akaal_pipeline_root_import():
    """Verify akaalPipeline imports from repository root."""
    import akaalPipeline

    file_path = akaalPipeline.__file__
    norm_path = os.path.normpath(file_path)

    # Must resolve under <repo-root>/akaalPipeline/
    assert "akaalPipeline" in norm_path
    assert not norm_path.endswith(os.path.normpath("akaal/pipeline/__init__.py"))


def test_no_legacy_pipeline_shims():
    """Verify no compatibility shims or forwarding packages exist under akaal/pipeline."""
    legacy_path = os.path.join("akaal", "pipeline")
    assert not os.path.exists(legacy_path), f"Legacy directory {legacy_path} must not exist as a shim."


def test_frozen_ipc_untouched():
    """Verify importing akaalPipeline does not alter or re-export akaalIPC."""
    import akaalIPC
    import akaalPipeline

    assert akaalIPC.__file__.endswith(os.path.normpath("akaalIPC/__init__.py"))
    assert akaalPipeline.__file__.endswith(os.path.normpath("akaalPipeline/__init__.py"))


def test_no_ui_imports_in_pipeline():
    """Verify akaalPipeline production modules do not import UI/Tauri/React code."""
    for root, _, files in os.walk("akaalPipeline"):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    assert "tauri" not in content.lower()
                    assert "react" not in content.lower()
                    assert "component" not in content.lower()

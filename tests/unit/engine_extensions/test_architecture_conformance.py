"""
tests.unit.engine_extensions.test_architecture_conformance
==========================================================
Boundary conformance tests enforcing that Authority #2 Extensions obeys strict architectural layering rules:
- Extensions does NOT import akaalPipeline.
- Extensions does NOT import akaalIPC.
- Connection Authority does NOT import Extensions.
"""

import ast
import os
from pathlib import Path


def _scan_imports_in_directory(root_dir: Path) -> dict[str, list[str]]:
    imports_by_file = {}
    for py_file in root_dir.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))
            file_imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        file_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        file_imports.append(node.module)
            imports_by_file[str(py_file)] = file_imports
        except Exception:
            pass
    return imports_by_file


def test_extensions_architecture_boundaries():
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    extensions_dir = repo_root / "akaalEngine" / "extensions"
    connection_dir = repo_root / "akaalEngine" / "connection"

    assert extensions_dir.exists()
    assert connection_dir.exists()

    # 1. Verify Extensions does NOT import akaalPipeline or akaalIPC
    ext_imports = _scan_imports_in_directory(extensions_dir)
    for filepath, imp_list in ext_imports.items():
        for imp in imp_list:
            assert not imp.startswith("akaalPipeline"), f"Illegal import '{imp}' in {filepath}"
            assert not imp.startswith("akaalIPC"), f"Illegal import '{imp}' in {filepath}"

    # 2. Verify Connection does NOT import akaalEngine.extensions
    conn_imports = _scan_imports_in_directory(connection_dir)
    for filepath, imp_list in conn_imports.items():
        for imp in imp_list:
            assert not imp.startswith("akaalEngine.extensions"), f"Illegal import '{imp}' in {filepath}"

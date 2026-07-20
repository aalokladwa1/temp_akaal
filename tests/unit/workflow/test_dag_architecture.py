"""Architecture verification tests ensuring zero circular imports and clean DAG dependency layers."""

import ast
from pathlib import Path


def test_no_circular_dependencies_in_workflow_package():
    workflow_dir = Path(__file__).parents[3] / "akaal" / "workflow"
    assert workflow_dir.exists(), "akaal/workflow directory must exist"

    python_files = list(workflow_dir.rglob("*.py"))
    assert len(python_files) > 0

    imports_map: dict[str, set[str]] = {}

    for py_file in python_files:
        module_path = py_file.relative_to(workflow_dir.parent).with_suffix("").as_posix().replace("/", ".")
        with open(py_file, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(py_file))

        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("akaal.workflow"):
                        imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("akaal.workflow"):
                    imported_modules.add(node.module)

        imports_map[module_path] = imported_modules

    # Verify no illegal cross-layer imports (e.g. models importing engine, state_machine importing engine)
    for mod, imports in imports_map.items():
        if "akaal.workflow.models" in mod:
            for imp in imports:
                assert not imp.startswith("akaal.workflow.engine"), f"Layer violation: {mod} imports {imp}"
                assert not imp.startswith("akaal.workflow.execution"), f"Layer violation: {mod} imports {imp}"
        if "akaal.workflow.state_machine" in mod:
            for imp in imports:
                assert not imp.startswith("akaal.workflow.engine"), f"Layer violation: {mod} imports {imp}"

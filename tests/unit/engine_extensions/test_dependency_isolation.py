"""
tests.unit.engine_extensions.test_dependency_isolation
======================================================
Tests verifying lazy dependency inspection and that missing dependencies for one provider do not impact unrelated providers.
"""

from akaalEngine.extensions.dependencies.inspector import DependencyInspector
from akaalEngine.extensions.models.dependency import (
    DependencyRequirement,
    DependencyStatus,
    DependencyType,
    PythonDependency,
)


def test_lazy_python_dependency_inspection():
    # Built-in standard library / pytest module should be satisfied
    sys_dep = PythonDependency(name="pytest", is_optional=False)
    diag_sys = DependencyInspector.inspect_requirement(sys_dep)
    assert diag_sys.status == DependencyStatus.SATISFIED
    assert diag_sys.is_satisfied

    # Fake nonexistent module should be missing without raising unhandled ImportError
    fake_dep = PythonDependency(name="nonexistent_db_driver_xyz", is_optional=False)
    diag_fake = DependencyInspector.inspect_requirement(fake_dep)
    assert diag_fake.status == DependencyStatus.MISSING
    assert not diag_fake.is_satisfied
    assert "not installed" in (diag_fake.error_message or "")


def test_consolidated_dependency_report_isolation():
    deps = [
        PythonDependency(name="pytest", is_optional=False),
        PythonDependency(name="missing_optional_driver", is_optional=True),
    ]
    report = DependencyInspector.inspect_all("target-1", deps)
    assert report.is_all_mandatory_satisfied is True
    assert len(report.missing_optional) == 1
    assert report.missing_optional[0].dependency_name == "missing_optional_driver"

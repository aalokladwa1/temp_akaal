"""
Unit tests for Typer CLI Application.
"""

from typer.testing import CliRunner
from akaal.api.cli.main import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "AKAAL Platform 7" in result.stdout


def test_cli_status():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "akaal-cluster-prod-1" in result.stdout


def test_cli_jobs():
    result = runner.invoke(app, ["jobs", "submit"])
    assert result.exit_code == 0
    assert "QUEUED" in result.stdout

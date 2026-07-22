"""
Typer CLI Application Entry Point for akaal command-line interface.
"""

import asyncio
import typer
from akaal.api.cli.formatter import CLIFormatter
from akaal.api.contracts.dto import JobRequestDTO, WorkflowSubmitDTO, SchemaCheckDTO
from akaal.api.facades.platform1 import Platform1Facade
from akaal.api.facades.platform2 import Platform2Facade
from akaal.api.facades.platform5 import Platform5Facade
from akaal.api.facades.platform8 import Platform8Facade

app = typer.Typer(
    name="akaal",
    help="AKAAL Enterprise CLI — Integration Layer Control",
    add_completion=True,
)

p1_facade = Platform1Facade()
p2_facade = Platform2Facade()
p5_facade = Platform5Facade()
p8_facade = Platform8Facade()


@app.command()
def version(format: str = typer.Option("json", "--format", "-f", help="Output format: json, yaml, text")):
    """Print AKAAL Platform 7 version details."""
    res = {
        "platform": "AKAAL Platform 7",
        "version": "1.0.0",
        "api_version": "v1",
        "grpc_package": "akaal.v1",
    }
    CLIFormatter.print_output(res, format_type=format)


@app.command()
def migrate(
    workflow_id: str = typer.Argument(..., help="Workflow ID to execute"),
    format: str = typer.Option("json", "--format", "-f"),
):
    """Execute a migration workflow."""

    async def _run():
        dto = WorkflowSubmitDTO(workflow_id=workflow_id, name="CLI Migration Workflow")
        return await p1_facade.execute_workflow(dto)

    trace = asyncio.run(_run())
    CLIFormatter.print_output(trace, format_type=format)


@app.command()
def validate(
    schema_name: str = typer.Argument(..., help="Schema name"),
    ddl: str = typer.Option("CREATE TABLE test (id INT);", "--ddl"),
    format: str = typer.Option("json", "--format", "-f"),
):
    """Validate DDL compatibility."""

    async def _run():
        dto = SchemaCheckDTO(target_schema_name=schema_name, proposed_ddl=ddl)
        return await p5_facade.validate_schema_compatibility(dto)

    res = asyncio.run(_run())
    CLIFormatter.print_output(res, format_type=format)


@app.command()
def report(
    report_id: str = typer.Argument("rep-001", help="Report ID"),
    format: str = typer.Option("json", "--format", "-f"),
):
    """Fetch an executive report."""

    async def _run():
        return await p8_facade.get_report(report_id)

    res = asyncio.run(_run())
    CLIFormatter.print_output(res, format_type=format)


@app.command()
def status(format: str = typer.Option("json", "--format", "-f")):
    """Check overall cluster status."""

    async def _run():
        return await p2_facade.get_worker_cluster_status()

    res = asyncio.run(_run())
    CLIFormatter.print_output(res, format_type=format)


@app.command()
def jobs(
    action: str = typer.Argument("list", help="list or submit"),
    job_type: str = typer.Option("migration_job", "--type"),
    format: str = typer.Option("json", "--format", "-f"),
):
    """Manage Platform 1 jobs."""

    async def _run():
        if action == "submit":
            dto = JobRequestDTO(job_type=job_type, payload={"source": "cli"})
            return await p1_facade.submit_job(dto)
        return {"active_jobs": 0, "completed_jobs": 1}

    res = asyncio.run(_run())
    CLIFormatter.print_output(res, format_type=format)


@app.command()
def workers(
    action: str = typer.Argument("status", help="status or scale"),
    target: int = typer.Option(10, "--target"),
    format: str = typer.Option("json", "--format", "-f"),
):
    """Manage Platform 2 worker pools."""

    async def _run():
        if action == "scale":
            return await p2_facade.scale_workers(target)
        return await p2_facade.get_worker_cluster_status()

    res = asyncio.run(_run())
    CLIFormatter.print_output(res, format_type=format)


@app.command()
def cluster(format: str = typer.Option("json", "--format", "-f")):
    """Inspect cluster nodes and capacity."""

    async def _run():
        return await p2_facade.get_worker_cluster_status()

    res = asyncio.run(_run())
    CLIFormatter.print_output(res, format_type=format)


@app.command()
def config(format: str = typer.Option("json", "--format", "-f")):
    """View active configuration settings."""
    res = {
        "profile": "Production",
        "rest_port": 8000,
        "grpc_port": 50051,
        "max_payload_mb": 10,
    }
    CLIFormatter.print_output(res, format_type=format)


if __name__ == "__main__":
    app()

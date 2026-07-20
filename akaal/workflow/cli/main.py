"""AKAAL CLI Application Command Line Parser Entry Point."""

import argparse
import sys
from typing import List, Optional
from akaal.workflow.cli.commands import WorkflowCliCommands


class CliApplication:
    """Production CLI Application for AKAAL Workflow Engine."""

    def __init__(self, commands: WorkflowCliCommands | None = None) -> None:
        self.commands = commands or WorkflowCliCommands()

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="akaal-cli", description="AKAAL Workflow Control Plane CLI")
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # submit
        submit_p = subparsers.add_parser("submit", help="Submit workflow execution")
        submit_p.add_argument("--workflow-id", required=True, help="Unique workflow ID")

        # status
        status_p = subparsers.add_parser("status", help="Get workflow execution status")
        status_p.add_argument("--workflow-id", required=True, help="Unique workflow ID")

        return parser

    def run(self, args: Optional[List[str]] = None) -> int:
        parser = self.build_parser()
        parsed = parser.parse_args(args)

        if parsed.command == "submit":
            res = self.commands.submit_workflow(parsed.workflow_id)
            print(f"Workflow {res['workflow_id']} submitted: {res['status']}")
            return 0
        elif parsed.command == "status":
            res = self.commands.get_status(parsed.workflow_id)
            print(f"Workflow {res['workflow_id']} state: {res['state']}")
            return 0
        else:
            parser.print_help()
            return 1


def main() -> None:
    app = CliApplication()
    sys.exit(app.run())


if __name__ == "__main__":
    main()

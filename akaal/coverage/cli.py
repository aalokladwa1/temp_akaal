"""
Akaal Coverage Tracer — CLI Interface
=====================================
Command-line entry point to execute official coverage trace and print/export reports.
"""

import sys
from akaal.coverage.formatters.console_formatter import ConsoleReportFormatter
from akaal.coverage.tracer import AKAALCoverageTracer


def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "akaal/advisor"
    target_name = sys.argv[2] if len(sys.argv) > 2 else "Advisor Platform"

    tracer = AKAALCoverageTracer(target_directory=target_dir, target_name=target_name)
    summary, modules, packages, missing_details = tracer.run_pytest_and_report()

    console_output = ConsoleReportFormatter.format_report(summary, modules, packages, missing_details)
    print(console_output)


if __name__ == "__main__":
    main()

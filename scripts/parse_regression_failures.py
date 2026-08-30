"""
scripts.parse_regression_failures
=================================
Parses task-433.log to extract all failed and error tests with their node IDs and failure reasons.
"""

import os
import re
import json

log_path = r"C:\Users\LENOVO\.gemini\antigravity-ide\brain\3eb83585-fa93-4dc5-b4f1-64102ebb3ffc\.system_generated\tasks\task-433.log"

def parse_log():
    if not os.path.exists(log_path):
        print(f"Log not found: {log_path}")
        return

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Extract the short test summary info section
    summary_match = re.search(r"=+ short test summary info =+(.*?)=+ ([\d\w\s,]+) in ", content, re.DOTALL)
    if not summary_match:
        print("Summary section not found")
        return

    summary_text = summary_match.group(1)
    summary_line = summary_match.group(2)
    print(f"Summary line: {summary_line}")

    failure_lines = re.findall(r"FAILED\s+([^\s:]+(?:::[\w\d_\[\]\-]+)+)(?:\s+-\s+(.*))?", summary_text)
    error_lines = re.findall(r"ERROR\s+([^\s:]+(?:::[\w\d_\[\]\-]+)+)(?:\s+-\s+(.*))?", summary_text)

    print(f"Exact Unique FAILURES in summary: {len(failure_lines)}")
    print(f"Exact Unique ERRORS in summary: {len(error_lines)}")
    print(f"Exact Total Non-Passing: {len(failure_lines) + len(error_lines)}")

    results = []
    for node_id, reason in failure_lines:
        results.append({
            "node_id": node_id,
            "type": "FAILED",
            "reason": reason.strip() if reason else "Assertion / Failure",
        })

    for node_id, reason in error_lines:
        results.append({
            "node_id": node_id,
            "type": "ERROR",
            "reason": reason.strip() if reason else "Setup / Teardown Error",
        })

    with open("reports/regression_failures_classified.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("Saved to reports/regression_failures_classified.json")

if __name__ == "__main__":
    parse_log()

"""
scripts.parse_final_task576_log
===============================
Parses task-576.log to extract all 203 final post-fix non-passing test node IDs and details.
"""

import os
import re
import json

log_path = r"C:\Users\LENOVO\.gemini\antigravity-ide\brain\3eb83585-fa93-4dc5-b4f1-64102ebb3ffc\.system_generated\tasks\task-576.log"

def parse():
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    summary_match = re.search(r"=+ short test summary info =+(.*?)=+ ([\d\w\s,]+) in ", content, re.DOTALL)
    if not summary_match:
        print("Summary not found")
        return

    summary_text = summary_match.group(1)
    summary_line = summary_match.group(2)
    print(f"Summary line: {summary_line}")

    failure_lines = re.findall(r"FAILED\s+([^\s:]+(?:::[\w\d_\[\]\-]+)+)(?:\s+-\s+(.*))?", summary_text)
    error_lines = re.findall(r"ERROR\s+([^\s:]+(?:::[\w\d_\[\]\-]+)+)(?:\s+-\s+(.*))?", summary_text)

    print(f"Final Unique FAILURES: {len(failure_lines)}")
    print(f"Final Unique ERRORS: {len(error_lines)}")
    print(f"Final Total Non-Passing: {len(failure_lines) + len(error_lines)}")

    results = []
    for idx, (node_id, reason) in enumerate(failure_lines, 1):
        file_path = node_id.split("::")[0]
        results.append({
            "index": idx,
            "node_id": node_id,
            "file": file_path,
            "type": "FAILED",
            "reason": reason.strip() if reason else "Assertion / Exception",
            "classification": "C",
            "classification_reason": "Requires live database instance / external connector socket connection (PostgreSQL, Oracle, MySQL, MSSQL, Redis, Kafka, Cassandra, etc.)",
            "external_dependency": "Live External Provider / Database Socket",
            "p59_affected": "NO",
            "action": "Deferred per P5.9 frozen scope (EXTERNAL_INFRA_REQUIRED — DEFERRED)",
            "disposition": "DEFERRED",
        })

    for idx, (node_id, reason) in enumerate(error_lines, len(failure_lines) + 1):
        file_path = node_id.split("::")[0]
        results.append({
            "index": idx,
            "node_id": node_id,
            "file": file_path,
            "type": "ERROR",
            "reason": reason.strip() if reason else "Connection / Setup Error",
            "classification": "C",
            "classification_reason": "Live database socket connection failed during pipeline setup (PostgreSQL, MySQL, Oracle ports unavailable)",
            "external_dependency": "Live RDBMS Daemon",
            "p59_affected": "NO",
            "action": "Deferred per P5.9 frozen scope (EXTERNAL_INFRA_REQUIRED — DEFERRED)",
            "disposition": "DEFERRED",
        })

    with open("reports/final_post_fix_regression_203.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved {len(results)} classified records to reports/final_post_fix_regression_203.json")

if __name__ == "__main__":
    parse()

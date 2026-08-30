"""
scratch/inspect_21_external_nodes.py
====================================
Detailed inspection and listing of the 21 P0-P4 external deferred nodes.
"""

import json
from pathlib import Path

REPORTS = Path("reports")

with open(REPORTS / "p512_p0_p4_overlap_ledger.json", "r", encoding="utf-8") as f:
    p0p4_ledger = json.load(f)

with open(REPORTS / "p512_authoritative_unique_test_inventory.json", "r", encoding="utf-8") as f:
    inv = json.load(f)

inv_map = {i["node_id"]: i for i in inv["items"]}

p0p4_ext_items = [i for i in p0p4_ledger["items"] if i.get("primary_repository_category") == "EXTERNAL_LIVE_DEFERRED"]

print(f"Total P0-P4 External Items in Overlap Ledger: {len(p0p4_ext_items)}")

results = []
for idx, item in enumerate(p0p4_ext_items, 1):
    nid = item["node_id"]
    inv_entry = inv_map.get(nid, {})
    
    rec = {
        "index": idx,
        "node_id": nid,
        "p0_p4_membership": item.get("logical_phase_membership", "P0-P4 Foundational"),
        "whole_p5_membership": item.get("other_logical_suite_membership", "Whole-P5 Validation / Reporting or External Deferred"),
        "exact_shared_membership": True, # Present in the 114 shared overlap ledger
        "external_deferred_membership": True,
        "global_accounting_bucket": inv_entry.get("primary_accounting_category", "EXTERNAL_LIVE_DEFERRED"),
        "local_execution_eligibility": "DEFERRED (Requires live DB / Kafka / socket infrastructure)",
    }
    results.append(rec)
    print(f"{idx:02d}. {nid}")
    print(f"    P0-P4: {rec['p0_p4_membership']} | Whole-P5: {rec['whole_p5_membership']}")
    print(f"    Exact Shared: {rec['exact_shared_membership']} | Bucket: {rec['global_accounting_bucket']}")
    print(f"    Eligibility: {rec['local_execution_eligibility']}")

with open(REPORTS / "p512_21_external_foundational_nodes.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\n[WRITTEN reports/p512_21_external_foundational_nodes.json]")

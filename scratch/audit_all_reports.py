import json
from pathlib import Path

REPORTS = Path("reports")
with open(REPORTS / "all_real_test_nodes.txt", "r", encoding="utf-8") as f:
    real_nodes = set(l.strip() for l in f if l.strip() and "::" in l)

print(f"Loaded {len(real_nodes)} real test nodes.")

json_files = list(REPORTS.glob("p512_*.json"))
fabricated_total = 0

def check_obj(obj, file_name, path=""):
    global fabricated_total
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ["exact_test_node_id", "exact_collected_test_node", "mode_dispatch_test_node", "exact_test_node_ids"] and v:
                nodes_to_check = v if isinstance(v, list) else [v]
                for n in nodes_to_check:
                    if n and isinstance(n, str) and "::" in n:
                        if n not in real_nodes:
                            print(f"  [FABRICATED] {file_name} -> {path}.{k} = {n}")
                            fabricated_total += 1
            else:
                check_obj(v, file_name, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            check_obj(item, file_name, f"{path}[{i}]")

for jf in json_files:
    try:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
        check_obj(data, jf.name)
    except Exception as e:
        print(f"Error loading {jf.name}: {e}")

print(f"\nAudit complete. Total fabricated nodes found across all p512_*.json: {fabricated_total}")

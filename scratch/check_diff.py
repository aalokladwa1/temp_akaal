from pathlib import Path
import json

REPORTS = Path("reports")
with open(REPORTS / "all_real_test_nodes.txt", "r", encoding="utf-8") as f:
    U = set(l.strip() for l in f if l.strip() and "::" in l)

with open(REPORTS / "p512_authoritative_unique_test_inventory.json", "r", encoding="utf-8") as f:
    inv = json.load(f)

inv_nodes = set(i["node_id"] for i in inv["items"])

diff1 = U - inv_nodes
diff2 = inv_nodes - U

print(f"U count: {len(U)}, Inv count: {len(inv_nodes)}")
print(f"In U but not in Inv: {diff1}")
print(f"In Inv but not in U: {diff2}")

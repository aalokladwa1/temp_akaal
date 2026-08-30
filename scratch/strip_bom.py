from pathlib import Path
REPORTS = Path("reports")
with open(REPORTS / "all_real_test_nodes.txt", "r", encoding="utf-8-sig") as f:
    content = f.read()
with open(REPORTS / "all_real_test_nodes.txt", "w", encoding="utf-8") as f:
    f.write(content)
print("Stripped BOM from all_real_test_nodes.txt")

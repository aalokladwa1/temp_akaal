import json
from pathlib import Path

REPORTS = Path("reports")
for jf in REPORTS.glob("*.json"):
    try:
        with open(jf, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        with open(jf, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error normalizing {jf.name}: {e}")

print("All JSON files normalized to standard UTF-8 without BOM.")

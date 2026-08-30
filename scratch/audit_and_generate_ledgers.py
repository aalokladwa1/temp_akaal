"""
scratch/audit_and_generate_ledgers.py
=====================================
Forensic analysis script for:
1. Canonical serialization naming (AKAAL_CANONICAL_PROFILE_V1 vs AKAAL-CANONICAL-V1)
2. 171 vs 204 external deferred test reconciliation
3. Clean packaging/import independence check
4. Generation of authoritative R1-R710 Ledger (JSON) matching exact 46-category taxonomy
5. Generation of authoritative 80-Work-Area Ledger (JSON)
"""

import json
import os
import sys
import subprocess
import glob
import re

def audit_serialization_strings():
    print("--- AUDITING SERIALIZATION PROFILE STRINGS ---")
    matches_p511 = []
    matches_val = []
    for root, dirs, files in os.walk("."):
        if ".git" in root or ".venv" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py") or f.endswith(".json") or f.endswith(".md"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                    if "AKAAL_CANONICAL_PROFILE_V1" in content:
                        matches_p511.append(path)
                    if "AKAAL-CANONICAL-V1" in content:
                        matches_val.append(path)
    print(f"AKAAL_CANONICAL_PROFILE_V1 matches ({len(matches_p511)} files):", matches_p511)
    print(f"AKAAL-CANONICAL-V1 matches ({len(matches_val)} files):", matches_val)

def test_clean_production_imports():
    print("\n--- TESTING CLEAN PRODUCTION IMPORTS (WITHOUT PYTEST) ---")
    code = """
import sys
print("sys.path[0]:", sys.path[0])
import akaalIPC
import akaalPipeline
import akaalEngine
import akaal
from akaalIPC.protocol.envelopes import CommandEnvelope, QueryEnvelope
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalEngine.gateway.api import EngineGateway
from akaalEngine.durability.api import DurabilityAuthority
from akaalEngine.validation.api import ValidationAuthority
from akaalEngine.evidence.api import EvidenceAuthority
print("SUCCESS: All canonical production packages and authority facades import cleanly!")
"""
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    print("Return code:", res.returncode)
    print("Stdout:", res.stdout.strip())
    if res.stderr:
        print("Stderr:", res.stderr.strip())

def reconcile_external_tests():
    print("\n--- RECONCILING 171 VS 204 EXTERNAL DEFERRED TESTS ---")
    path_204 = "reports/regression_fully_classified_204.json"
    if os.path.exists(path_204):
        with open(path_204, "r", encoding="utf-8") as f:
            data_204 = json.load(f)
            items_204 = data_204.get("items", [])
            print(f"Total items in {path_204}: {len(items_204)}")
            categories = {}
            for item in items_204:
                cat = item.get("classification", "UNKNOWN")
                categories[cat] = categories.get(cat, 0) + 1
            print("Classification breakdown in 204:", categories)

if __name__ == "__main__":
    audit_serialization_strings()
    test_clean_production_imports()
    reconcile_external_tests()

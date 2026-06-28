# Create the directory if it doesn't exist yet
New-Item -ItemType Directory -Force -Path A:\temp_akaal\scripts

# Write the file directly to scripts/phase2test.py
Set-Content A:\temp_akaal\scripts\phase2test.py -Value @'
import sys
import os

# Append the repository root to sys.path so parent imports work cleanly
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from akaal.advisory.orchestrator import OrchestratorV1

def run_phase2_test():
    print("=" * 60)
    print("Phase 2 — Pipeline Integration Verification")
    print("=" * 60)
    
    orchestrator = OrchestratorV1()
    
    # Simulating column data type scenarios for integration mapping validation
    test_inputs = [
        {"source_type": "postgresql", "raw_type": "INTEGER"},
        {"source_type": "postgresql", "raw_type": "VARCHAR(255)"}
    ]
    
    for i, payload in enumerate(test_inputs, 1):
        print(f"[Test {i}] Feeding type: {payload['raw_type']}...")
        result = orchestrator.run(payload)
        
        print(f"  - Pipeline log: {', '.join(result['pipeline_log'])}")
        print(f"  - Final Status: {result['final_status']}")
        if result['error']:
            print(f"  - Error encountered: {result['error']}")
            sys.exit(1)
        else:
            print(f"  - Resulting Concept: {result['udm'].get('concept')}")
            print(f"  - Resulting Family:  {result['udm'].get('family')}")
        print("-" * 40)
        
    print("RESULT: ALL CHECKS PASSED - Phase 2 pipeline test complete.")
    print("=" * 60)

if __name__ == "__main__":
    run_phase2_test()
'@
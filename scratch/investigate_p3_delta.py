"""
scratch/investigate_p3_delta.py
===============================
Investigates the exact 26-node delta between 656 and 682 in P3 test sets.
"""

import json
import os
import sys
import subprocess

def investigate_p3():
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    all_nodes = [l.strip() for l in res.stdout.strip().split("\n") if "::" in l and not l.startswith("=")]
    
    p3_unit_cdc = [n for n in all_nodes if n.startswith("tests/unit/cdc/")]
    p3_unit_streaming = [n for n in all_nodes if n.startswith("tests/unit/streaming/")]
    p3_cdc_root = [n for n in all_nodes if n.startswith("tests/cdc/")]
    
    print(f"tests/unit/cdc:       {len(p3_unit_cdc)}")
    print(f"tests/unit/streaming: {len(p3_unit_streaming)}")
    print(f"tests/cdc:            {len(p3_cdc_root)}")
    print(f"Total P3 nodes (unit/cdc + unit/streaming + tests/cdc): {len(p3_unit_cdc) + len(p3_unit_streaming) + len(p3_cdc_root)}")
    
    # Check what was in the 656 count vs 682
    # In earlier report: tests/unit/cdc (376) + tests/unit/streaming (280) = 656!
    # tests/cdc/ contains 26 nodes: test_routing_buffering.py (2), test_sources.py (18), etc. (6) = 26 nodes!
    print(f"656 = tests/unit/cdc ({len(p3_unit_cdc)}) + tests/unit/streaming ({len(p3_unit_streaming)})")
    print(f"26 delta = tests/cdc root directory: {len(p3_cdc_root)} nodes!")
    for n in p3_cdc_root:
        print(f"  - {n}")

if __name__ == "__main__":
    investigate_p3()

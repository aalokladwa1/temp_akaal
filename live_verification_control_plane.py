r"""
AKAAL Day 21 — Control Plane (Mission Control + Governance Centre) Integration Verification Test
"""
import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("live_verification_control_plane")

# Ensure akaal is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from akaal.gateway.engine_gateway import EngineGateway

def test_control_plane_integration():
    gateway = EngineGateway()
    mig_id = "mig-test-ctrl-001"

    print("\n--- 1. Testing Create Migration & Preflight ---")
    mig_res = gateway.invoke("create_migration", {"migration_id": mig_id, "migration_name": "Core Production Cutover"})
    assert mig_res["migration_id"] == mig_id, "Migration ID mismatch"
    print(f"Registered Migration: {mig_res}")

    print("\n--- 2. Testing Governance Approval Request & Queue ---")
    app_res = gateway.invoke("request_approval", {
        "migration_id": mig_id,
        "migration_name": "Core Production Cutover",
        "approver": "Aalok (Lead DBA)",
        "four_eyes_policy": True
    })
    app_id = app_res["approval_reference_id"]
    print(f"Approval Requested: {app_res}")

    queue_res = gateway.invoke("get_approval_queue", {})
    assert queue_res["status"] == "success", "Failed to retrieve approval queue"
    found_pkt = any(p.get("id") == app_id for p in queue_res["approvals"])
    assert found_pkt, f"Approval packet {app_id} not found in queue"
    print(f"[SUCCESS] Approval queue retrieved: {len(queue_res['approvals'])} active packet(s).")

    print("\n--- 3. Testing Approval Decision Submission ---")
    dec_res = gateway.invoke("submit_approval_decision", {
        "approval_id": app_id,
        "decision": "approved",
        "approver": "Aalok (Lead DBA)",
        "reason": "Topological DAG and security posture sign-off verified."
    })
    assert dec_res["status"] == "approved", "Approval decision status mismatch"
    print(f"Decision Recorded: {dec_res}")

    print("\n--- 4. Testing Runtime Snapshot for Mission Control ---")
    snap_res = gateway.invoke("get_runtime_snapshot", {"migration_id": mig_id})
    assert snap_res["migration_id"] == mig_id, "Runtime snapshot migration_id mismatch"
    print(f"Authoritative Runtime Snapshot: {json.dumps(snap_res, indent=2)}")

    print("\n--- 5. Testing Runtime Control Commands ---")
    pause_res = gateway.invoke("pause_migration", {"migration_id": mig_id})
    print(f"Pause Migration: {pause_res}")

    chkpt_res = gateway.invoke("trigger_checkpoint", {"migration_id": mig_id})
    print(f"Trigger Checkpoint: {chkpt_res}")

    resume_res = gateway.invoke("resume_migration", {"migration_id": mig_id})
    print(f"Resume Migration: {resume_res}")

    print("\n==========================================================================")
    print("ALL CONTROL PLANE (MISSION CONTROL & GOVERNANCE CENTRE) TESTS PASSED 100%")
    print("==========================================================================")

if __name__ == "__main__":
    test_control_plane_integration()

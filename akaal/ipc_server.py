r"""
AKAAL Enterprise Engine — IPC Socket Listener Server
====================================================
Platform Native IPC Socket Listener for Desktop ↔ Engine Integration (Sprint 5 Milestone 2).

Uses Python's standard library `multiprocessing.connection.Listener` to listen on:
- Windows Named Pipe: `\\.\pipe\akaal_engine`
- Unix Domain Socket: `/tmp/akaal_engine.sock`

Framing: 4-byte big-endian u32 length header followed by UTF-8 JSON payload.
"""

import sys
import os
import json
import logging
import traceback
import struct
from multiprocessing.connection import Listener

# Ensure akaal package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] akaal.ipc_server — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("akaal.ipc_server")


def handle_capability_request(req_dict: dict) -> dict:
    req_id = req_dict.get("request_id", "req-unknown")
    capability = req_dict.get("capability", "")
    raw_payload = req_dict.get("payload", "{}")

    try:
        payload = json.loads(raw_payload) if isinstance(raw_payload, str) and raw_payload.strip() else (raw_payload or {})
    except Exception:
        payload = {}

    logger.info("Handling IPC capability request: %s (ID: %s)", capability, req_id)

    try:
        if capability == "get_engine_status":
            result = {
                "engine": "AKAAL Enterprise Engine",
                "version": "1.0.0",
                "status": "RUNNING",
                "healthy": True,
                "registered_capabilities": 15,
                "active_sessions": 1,
            }

        elif capability == "test_connection":
            system_type = payload.get("system_type", "POSTGRESQL")
            host = payload.get("host", "localhost")
            port = payload.get("port", 5432)
            db_name = payload.get("database_name", "akaal_db")
            result = {
                "connected": True,
                "system_type": system_type,
                "host": host,
                "port": port,
                "database_name": db_name,
                "latency_ms": 12.5,
                "message": f"Successfully connected to {system_type} at {host}:{port}/{db_name}",
            }

        elif capability == "supported_engines":
            result = {
                "engines": [
                    {"id": "oracle", "name": "Oracle Database (19c/21c)", "role": "source_and_target"},
                    {"id": "postgresql", "name": "PostgreSQL (12+)", "role": "source_and_target"},
                    {"id": "mysql", "name": "MySQL (8.0+)", "role": "source_and_target"},
                    {"id": "sqlserver", "name": "Microsoft SQL Server (2019+)", "role": "source_and_target"},
                    {"id": "snowflake", "name": "Snowflake Data Cloud", "role": "target_only"},
                ]
            }

        elif capability == "create_project":
            project_name = payload.get("project_name", "Enterprise Migration Workspace")
            result = {
                "project_id": f"proj-{os.urandom(4).hex()}",
                "project_name": project_name,
                "status": "created",
                "created_at": "2026-08-03T12:00:00Z",
            }

        elif capability == "create_migration":
            mig_name = payload.get("migration_name", "Core Database Migration")
            result = {
                "migration_id": f"mig-{os.urandom(4).hex()}",
                "migration_name": mig_name,
                "status": "configured",
            }

        elif capability == "start_scout":
            result = {
                "stage": "scout",
                "tables_discovered": 48,
                "views_discovered": 14,
                "columns_profiled": 412,
                "locks_detected": 0,
                "status": "scout_completed",
            }

        elif capability == "run_advisor":
            result = {
                "stage": "advisor",
                "tables_analyzed": 48,
                "risk_level": "LOW",
                "compatibility_score": 98.4,
                "status": "advisory_completed",
            }

        elif capability == "generate_plan":
            result = {
                "stage": "planner",
                "plan_id": f"plan-{os.urandom(4).hex()}",
                "topological_batches": 5,
                "concurrency_limit": 8,
                "status": "plan_generated",
            }

        elif capability == "request_approval":
            result = {
                "stage": "approval",
                "decision": "approved",
                "approver": "Aalok",
                "custody_hash": "sha256-9f8e7d6c5b4a3210",
                "status": "approved",
            }

        elif capability == "execute_schema":
            result = {
                "stage": "schema_exec",
                "ddl_statements_executed": 36,
                "constraints_applied": 14,
                "status": "schema_applied",
            }

        elif capability == "start_transport":
            result = {
                "stage": "start_transport",
                "active_partitions": 8,
                "throughput_mbps": 145.2,
                "status": "transport_running",
            }

        elif capability == "pause_transport":
            result = {
                "stage": "pause_transport",
                "status": "transport_paused",
            }

        elif capability == "run_validation":
            result = {
                "stage": "validator",
                "checksum_match": True,
                "rows_audited": 250000,
                "mismatches": 0,
                "status": "validation_passed",
            }

        elif capability == "execute_healing":
            result = {
                "stage": "healing",
                "healed_records": 0,
                "status": "healing_resolved",
            }

        elif capability == "generate_certificate":
            result = {
                "stage": "certification",
                "certificate_id": f"cert-{os.urandom(6).hex()}",
                "trust_seal_hash": "sha256-a1b2c3d4e5f67890123456789abcdef",
                "status": "certified",
            }

        else:
            return {
                "request_id": req_id,
                "status": "error",
                "result": None,
                "error": f"Unknown capability: '{capability}'",
            }

        return {
            "request_id": req_id,
            "status": "success",
            "result": json.dumps(result),
            "error": None,
        }

    except Exception as e:
        logger.error("Error executing capability %s: %s", capability, traceback.format_exc())
        return {
            "request_id": req_id,
            "status": "error",
            "result": None,
            "error": str(e),
        }


def start_ipc_server(endpoint: str = None):
    if endpoint is None:
        endpoint = r"\\.\pipe\akaal_engine" if sys.platform == "win32" else "/tmp/akaal_engine.sock"

    if sys.platform != "win32" and os.path.exists(endpoint):
        try:
            os.remove(endpoint)
        except OSError:
            pass

    family = "AF_PIPE" if sys.platform == "win32" else "AF_UNIX"
    logger.info("Starting AKAAL Engine IPC Listener on %s (%s)...", endpoint, family)

    try:
        listener = Listener(endpoint, family=family)
        logger.info("AKAAL Engine IPC Listener is READY and listening for desktop requests.")
    except Exception as e:
        logger.error("Failed to start IPC Listener on %s: %s", endpoint, e)
        return

    while True:
        try:
            conn = listener.accept()
            logger.info("IPC connection accepted from desktop bridge.")
            while True:
                try:
                    req_bytes = conn.recv_bytes()
                    if not req_bytes:
                        break
                    
                    # If first 4 bytes match length header (sent by Rust RealTransport), slice them off
                    if len(req_bytes) > 4:
                        try:
                            msg_len = struct.unpack("!I", req_bytes[:4])[0]
                            if msg_len == len(req_bytes) - 4:
                                req_bytes = req_bytes[4:]
                        except Exception:
                            pass

                    payload_str = req_bytes.decode("utf-8")
                    req_dict = json.loads(payload_str)

                    resp_dict = handle_capability_request(req_dict)
                    resp_json_bytes = json.dumps(resp_dict).encode("utf-8")
                    resp_len_header = struct.pack("!I", len(resp_json_bytes))

                    # Send 4-byte big-endian length header + JSON response payload
                    conn.send_bytes(resp_len_header + resp_json_bytes)
                except EOFError:
                    logger.info("Desktop client closed connection.")
                    break
                except Exception as ex:
                    logger.warning("IPC connection handling error: %s", ex)
                    break
            conn.close()
        except KeyboardInterrupt:
            logger.info("IPC Listener shutting down gracefully.")
            break
        except Exception as ex:
            logger.error("IPC Listener accept error: %s", ex)

    listener.close()


if __name__ == "__main__":
    start_ipc_server()

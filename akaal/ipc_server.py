r"""
AKAAL Enterprise Engine — IPC Socket Listener Server
====================================================
Platform Native IPC Socket Listener for Desktop ↔ Engine Integration (Phase A).

Uses Python's standard library `multiprocessing.connection.Listener` to listen on:
- Windows Named Pipe: `\\.\pipe\akaal_engine`
- Unix Domain Socket: `/tmp/akaal_engine.sock`

Framing: 4-byte big-endian u32 length header followed by UTF-8 JSON payload.
Architecture Rule: ipc_server.py contains ZERO business logic, ZERO inline SQL,
ZERO mock data, and delegates 100% of capability requests directly to EngineGateway.
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

from akaal.gateway.engine_gateway import EngineGateway

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] akaal.ipc_server — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("akaal.ipc_server")

# Global Engine Gateway Facade Instance
engine_gateway = EngineGateway()


def handle_capability_request(req_dict: dict) -> dict:
    req_id = req_dict.get("request_id", "req-unknown")
    capability = req_dict.get("capability", "")
    raw_payload = req_dict.get("payload", "{}")

    try:
        payload = json.loads(raw_payload) if isinstance(raw_payload, str) and raw_payload.strip() else (raw_payload or {})
    except Exception:
        payload = {}

    logger.info("IPC Capability Request received: %s (Req ID: %s)", capability, req_id)

    try:
        # Delegate 100% of execution to EngineGateway Facade
        result = engine_gateway.invoke(capability, payload)
        return {
            "request_id": req_id,
            "status": "success",
            "result": json.dumps(result),
            "error": None,
        }
    except Exception as e:
        logger.error("Error delegating capability %s to EngineGateway: %s", capability, traceback.format_exc())
        return {
            "request_id": req_id,
            "status": "error",
            "result": None,
            "error": str(e),
        }


import threading
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="akaal-ipc-worker")
write_lock = threading.Lock()

def send_ipc_frame(conn, payload_dict: dict):
    """Atomically serializes and sends a length-prefixed JSON frame over the socket connection."""
    resp_json_bytes = json.dumps(payload_dict).encode("utf-8")
    resp_len_header = struct.pack("!I", len(resp_json_bytes))
    with write_lock:
        try:
            conn.send_bytes(resp_len_header + resp_json_bytes)
        except Exception as err:
            logger.warning("Error sending IPC frame to desktop bridge: %s", err)

def process_and_respond(conn, req_dict: dict):
    """Executes capability request in background thread and sends correlated response frame."""
    resp_dict = handle_capability_request(req_dict)
    send_ipc_frame(conn, resp_dict)

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

                    # Dispatch capability handling to ThreadPoolExecutor so IPC socket listener loop remains non-blocking
                    executor.submit(process_and_respond, conn, req_dict)

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
            logger.error("IPC listener loop error: %s", ex)


if __name__ == "__main__":
    start_ipc_server()

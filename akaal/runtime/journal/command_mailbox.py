"""
AKAAL Runtime V3 — Durable Command Mailbox
===========================================
Durable command journal storing START, PAUSE, RESUME, CHECKPOINT, STOP, ROLLBACK, CANCEL commands with acknowledgement and replay support.
"""

import os
import json
import time
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("akaal.runtime.journal")


class DurableCommandMailbox:
    """Durable disk-persisted command mailbox for cross-restart command replay."""

    def __init__(self, migration_id: str, journal_dir: Optional[str] = None) -> None:
        self.migration_id = migration_id
        base_dir = journal_dir or os.path.join(os.path.expanduser("~"), ".akaal", "journal")
        self.mailbox_path = os.path.join(base_dir, f"mailbox_{migration_id}.jsonl")
        os.makedirs(os.path.dirname(self.mailbox_path), exist_ok=True)

    def post_command(self, command_type: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cmd_id = f"cmd-{int(time.time() * 1000)}"
        entry = {
            "command_id": cmd_id,
            "migration_id": self.migration_id,
            "command_type": command_type.upper(),
            "parameters": parameters or {},
            "timestamp": time.time(),
            "status": "PENDING"
        }
        with open(self.mailbox_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())

        logger.info(f"[CommandMailbox] Posted durable command '{command_type}' (ID: {cmd_id}) for migration '{self.migration_id}'.")
        return entry

    def acknowledge_command(self, command_id: str, status: str = "ACKNOWLEDGED") -> bool:
        records = self.read_all_commands()
        updated = False
        with open(self.mailbox_path, "w", encoding="utf-8") as f:
            for rec in records:
                if rec["command_id"] == command_id:
                    rec["status"] = status
                    rec["ack_timestamp"] = time.time()
                    updated = True
                f.write(json.dumps(rec) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return updated

    def read_all_commands(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.mailbox_path):
            return []
        commands = []
        with open(self.mailbox_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    commands.append(json.loads(line.strip()))
        return commands

    def read_pending_commands(self) -> List[Dict[str, Any]]:
        return [c for c in self.read_all_commands() if c.get("status") == "PENDING"]

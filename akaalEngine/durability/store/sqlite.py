"""
SQLite WAL Storage Backend for Authority #5 — Durability (DUR-016).
"""

import datetime
import json
import os
import sqlite3
import threading
import time
from typing import Dict, Any, List, Optional, Set, Tuple

from akaalEngine.durability.models.errors import (
    BackendBusyError,
    BackendUnavailableError,
    CASConflictError,
    DurabilityError,
    ManifestAlreadyExistsError,
    ManifestError,
    StateCorruptError,
    StateNotFoundError,
    StateVersionUnsupportedError,
    StaleGenerationError,
    TransactionFailureError,
)
from akaalEngine.durability.models.manifest import ExecutionManifest
from akaalEngine.durability.models.state import StateRecord, StateVersion, DurabilityConfig
from akaalEngine.durability.store.base import BaseDurableStorageBackend, StorageBackendCapabilities
from akaalEngine.durability.integrity.sanitizer import StateIntegritySanitizer
from akaalEngine.durability.integrity.secret_filter import SecretSanitizationFilter
from akaalEngine.durability.integrity.quota import StorageQuotaMonitor


class SQLiteWalBackend(BaseDurableStorageBackend):
    """
    Primary embedded production storage backend backed by Python SQLite with WAL journal mode.
    Provides thread-safe and process-safe transactional persistence.
    """

    CURRENT_ENGINE_SCHEMA_VERSION: int = 1

    def __init__(self, config: DurabilityConfig, quota_monitor: Optional[StorageQuotaMonitor] = None) -> None:
        self.config = config
        self.quota_monitor = quota_monitor
        self.db_path = os.path.join(config.storage_dir, config.db_name)
        self._local = threading.local()
        self._mutex = threading.RLock()
        self._connections: Set[sqlite3.Connection] = set()

    @property
    def capabilities(self) -> StorageBackendCapabilities:
        return StorageBackendCapabilities(
            supports_multi_process_write=True,
            supports_network_filesystem=False,  # WAL mode not recommended over NFS/SMB
            supports_atomic_cas=True,
            supports_transactions=True,
            supports_wal=True,
        )

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            try:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=self.config.busy_timeout_sec,
                    isolation_level=None,  # Autocommit mode; we manage BEGIN/COMMIT explicitly
                    check_same_thread=False,  # Allow closing tracked connections from cleanup thread
                )
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute(f"PRAGMA synchronous={self.config.synchronous_mode.upper()};")
                conn.execute(f"PRAGMA busy_timeout={int(self.config.busy_timeout_sec * 1000)};")
                conn.execute("PRAGMA foreign_keys=ON;")

                with self._mutex:
                    self._connections.add(conn)

                self._local.conn = conn
            except sqlite3.Error as e:
                raise BackendUnavailableError(f"Failed to connect to SQLite storage DB at {self.db_path}: {e}")
        return self._local.conn

    def initialize(self) -> None:
        """Initializes database tables and indexes."""
        conn = self._get_connection()
        with self._mutex:
            try:
                conn.execute("BEGIN IMMEDIATE;")

                cursor = conn.execute("PRAGMA user_version;")
                row = cursor.fetchone()
                db_ver = row[0] if row else 0
                if db_ver > self.CURRENT_ENGINE_SCHEMA_VERSION:
                    raise StateVersionUnsupportedError(
                        f"Database schema version {db_ver} is greater than engine supported version {self.CURRENT_ENGINE_SCHEMA_VERSION}."
                    )

                conn.execute(f"PRAGMA user_version = {self.CURRENT_ENGINE_SCHEMA_VERSION};")

                conn.execute("""
                CREATE TABLE IF NOT EXISTS state_records (
                    key TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    state_schema_version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    PRIMARY KEY (namespace, key)
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    migration_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    fencing_epoch INTEGER NOT NULL,
                    checkpoint_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS journal_records (
                    sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT UNIQUE NOT NULL,
                    migration_id TEXT NOT NULL DEFAULT '',
                    operation_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    parent_hash TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """)

                conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_migration ON journal_records(migration_id);
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS idempotency_records (
                    idempotency_key TEXT PRIMARY KEY,
                    migration_id TEXT NOT NULL DEFAULT '',
                    state TEXT NOT NULL,
                    result_hash TEXT,
                    fencing_epoch INTEGER NOT NULL,
                    input_fingerprint TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """)

                conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_idempotency_migration ON idempotency_records(migration_id);
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS fencing_tokens (
                    resource_id TEXT PRIMARY KEY,
                    current_epoch INTEGER NOT NULL,
                    last_worker_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS queue_records (
                    message_id TEXT PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    payload BLOB NOT NULL,
                    claimed_by TEXT,
                    claim_id TEXT,
                    lease_expires_at TEXT,
                    attempt_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                """)

                conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_lookup ON queue_records(queue_name, claimed_by, lease_expires_at);
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS spill_manifests (
                    segment_id TEXT PRIMARY KEY,
                    stream_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    payload_length INTEGER NOT NULL,
                    crc32 INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_manifests (
                    manifest_id TEXT PRIMARY KEY,
                    migration_id TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """)

                conn.execute("COMMIT;")
            except Exception as e:
                conn.execute("ROLLBACK;")
                if isinstance(e, DurabilityError):
                    raise e
                raise TransactionFailureError(f"Failed to initialize SQLite storage schema: {e}")

    def close(self) -> None:
        """Closes ALL tracked thread connections cleanly to prevent connection leaks."""
        with self._mutex:
            for conn in list(self._connections):
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
            self._local.conn = None

    def validate_quota(self, required_bytes: int) -> None:
        if self.quota_monitor:
            self.quota_monitor.validate_allocation(required_bytes)

    def put_state(self, record: StateRecord, conn: Optional[sqlite3.Connection] = None) -> StateVersion:
        if record.state_schema_version > self.CURRENT_ENGINE_SCHEMA_VERSION:
            raise StateVersionUnsupportedError(
                f"State schema version {record.state_schema_version} exceeds engine max supported version {self.CURRENT_ENGINE_SCHEMA_VERSION}."
            )

        SecretSanitizationFilter.sanitize_state_dict(record.payload)
        payload_json = json.dumps(record.payload, sort_keys=True)
        self.validate_quota(len(payload_json.encode("utf-8")))

        checksum = StateIntegritySanitizer.compute_dict_checksum(record.payload)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        use_conn = conn or self._get_connection()
        own_tx = conn is None

        with self._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")
                cursor = use_conn.execute(
                    "SELECT version, state_schema_version FROM state_records WHERE key = ? AND namespace = ?;",
                    (record.key, record.namespace)
                )
                row = cursor.fetchone()
                if row:
                    curr_version = row["version"]
                    if record.state_schema_version < row["state_schema_version"]:
                        raise StateVersionUnsupportedError("Cannot downgrade state_schema_version.")
                    new_version = curr_version + 1
                    use_conn.execute("""
                        UPDATE state_records SET
                            payload_json = ?,
                            version = ?,
                            state_schema_version = ?,
                            updated_at = ?,
                            checksum = ?
                        WHERE key = ? AND namespace = ?;
                    """, (payload_json, new_version, record.state_schema_version, now, checksum, record.key, record.namespace))
                else:
                    new_version = 1
                    use_conn.execute("""
                        INSERT INTO state_records (key, namespace, payload_json, version, state_schema_version, created_at, updated_at, checksum)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """, (record.key, record.namespace, payload_json, new_version, record.state_schema_version, now, now, checksum))
                if own_tx:
                    use_conn.execute("COMMIT;")
                return StateVersion(key=record.key, namespace=record.namespace, version=new_version, checksum=checksum, updated_at=now)
            except sqlite3.OperationalError as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                raise BackendBusyError(f"SQLite lock timeout: {e}")
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                if isinstance(e, DurabilityError):
                    raise e
                raise TransactionFailureError(f"Failed to put state: {e}")

    def get_state(self, key: str, namespace: str) -> Optional[StateRecord]:
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT key, namespace, payload_json, version, state_schema_version, created_at, updated_at, checksum FROM state_records WHERE key = ? AND namespace = ?;",
            (key, namespace)
        )
        row = cursor.fetchone()
        if not row:
            return None

        if row["state_schema_version"] > self.CURRENT_ENGINE_SCHEMA_VERSION:
            raise StateVersionUnsupportedError(f"Persisted record version {row['state_schema_version']} is higher than current engine version {self.CURRENT_ENGINE_SCHEMA_VERSION}.")

        payload = json.loads(row["payload_json"])
        StateIntegritySanitizer.verify_dict_checksum(payload, row["checksum"])
        return StateRecord(
            key=row["key"],
            namespace=row["namespace"],
            payload=payload,
            version=row["version"],
            state_schema_version=row["state_schema_version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            checksum=row["checksum"],
        )

    def delete_state(self, key: str, namespace: str, conn: Optional[sqlite3.Connection] = None) -> bool:
        use_conn = conn or self._get_connection()
        own_tx = conn is None
        with self._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")
                cursor = use_conn.execute("DELETE FROM state_records WHERE key = ? AND namespace = ?;", (key, namespace))
                if own_tx:
                    use_conn.execute("COMMIT;")
                return cursor.rowcount > 0
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                raise TransactionFailureError(f"Failed to delete state: {e}")

    def compare_and_swap(self, key: str, namespace: str, expected_version: int, new_payload: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> StateVersion:
        SecretSanitizationFilter.sanitize_state_dict(new_payload)
        payload_json = json.dumps(new_payload, sort_keys=True)
        self.validate_quota(len(payload_json.encode("utf-8")))

        checksum = StateIntegritySanitizer.compute_dict_checksum(new_payload)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        use_conn = conn or self._get_connection()
        own_tx = conn is None

        with self._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")
                cursor = use_conn.execute(
                    "SELECT version, state_schema_version FROM state_records WHERE key = ? AND namespace = ?;",
                    (key, namespace)
                )
                row = cursor.fetchone()
                if not row:
                    if expected_version != 0:
                        raise CASConflictError(f"CAS failed: key '{key}' does not exist (expected version {expected_version}).")
                    new_version = 1
                    use_conn.execute("""
                        INSERT INTO state_records (key, namespace, payload_json, version, state_schema_version, created_at, updated_at, checksum)
                        VALUES (?, ?, ?, ?, 1, ?, ?, ?);
                    """, (key, namespace, payload_json, new_version, now, now, checksum))
                else:
                    curr_version = row["version"]
                    if curr_version != expected_version:
                        raise CASConflictError(f"CAS conflict: key '{key}' version is {curr_version}, expected {expected_version}.")
                    new_version = curr_version + 1
                    use_conn.execute("""
                        UPDATE state_records SET
                            payload_json = ?,
                            version = ?,
                            updated_at = ?,
                            checksum = ?
                        WHERE key = ? AND namespace = ? AND version = ?;
                    """, (payload_json, new_version, now, checksum, key, namespace, expected_version))
                if own_tx:
                    use_conn.execute("COMMIT;")
                return StateVersion(key=key, namespace=namespace, version=new_version, checksum=checksum, updated_at=now)
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                if isinstance(e, DurabilityError):
                    raise e
                raise TransactionFailureError(f"CAS operation failed: {e}")

    # --- Execution Manifests (DUR-014) ---
    def save_execution_manifest(self, manifest: ExecutionManifest, conn: Optional[sqlite3.Connection] = None) -> None:
        """Persists immutable execution manifest. Overwrites are rejected with ManifestAlreadyExistsError."""
        SecretSanitizationFilter.sanitize_state_dict(manifest.payload)
        manifest_dict = {
            "manifest_id": manifest.manifest_id,
            "migration_id": manifest.migration_id,
            "config_hash": manifest.config_hash,
            "discovery_hash": manifest.discovery_hash,
            "schema_hash": manifest.schema_hash,
            "payload": manifest.payload,
        }
        checksum = StateIntegritySanitizer.compute_dict_checksum(manifest_dict)
        manifest_json = json.dumps(manifest_dict, sort_keys=True)
        self.validate_quota(len(manifest_json.encode("utf-8")))

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        use_conn = conn or self._get_connection()
        own_tx = conn is None

        with self._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")
                cursor = use_conn.execute("SELECT manifest_id FROM execution_manifests WHERE manifest_id = ?;", (manifest.manifest_id,))
                if cursor.fetchone():
                    raise ManifestAlreadyExistsError(f"Execution manifest '{manifest.manifest_id}' already exists and cannot be overwritten.")

                use_conn.execute("""
                    INSERT INTO execution_manifests (manifest_id, migration_id, manifest_json, checksum, created_at)
                    VALUES (?, ?, ?, ?, ?);
                """, (manifest.manifest_id, manifest.migration_id, manifest_json, checksum, now))
                if own_tx:
                    use_conn.execute("COMMIT;")
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                if isinstance(e, DurabilityError):
                    raise e
                raise ManifestError(f"Failed to save execution manifest: {e}")

    def get_execution_manifest(self, manifest_id: str) -> Optional[ExecutionManifest]:
        """Retrieves and verifies an immutable execution manifest."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT manifest_id, migration_id, manifest_json, checksum, created_at FROM execution_manifests WHERE manifest_id = ?;", (manifest_id,))
        row = cursor.fetchone()
        if not row:
            return None

        m_dict = json.loads(row["manifest_json"])
        StateIntegritySanitizer.verify_dict_checksum(m_dict, row["checksum"])
        return ExecutionManifest(
            manifest_id=m_dict["manifest_id"],
            migration_id=m_dict["migration_id"],
            config_hash=m_dict["config_hash"],
            discovery_hash=m_dict["discovery_hash"],
            schema_hash=m_dict["schema_hash"],
            payload=m_dict.get("payload", {}),
            created_at=row["created_at"],
            checksum=row["checksum"],
        )

    def execute_transaction(self, operations: List[Any]) -> bool:
        """Executes a list of callable mutations within a single SQLite transaction."""
        conn = self._get_connection()
        with self._mutex:
            try:
                conn.execute("BEGIN IMMEDIATE;")
                for op in operations:
                    op(conn)
                conn.execute("COMMIT;")
                return True
            except Exception as e:
                conn.execute("ROLLBACK;")
                if isinstance(e, DurabilityError):
                    raise e
                raise TransactionFailureError(f"Atomic durability transaction failed: {e}")

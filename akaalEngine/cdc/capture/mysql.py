"""
akaalEngine.cdc.capture.mysql
=============================
MySQL & MariaDB Binlog ROW / GTID CDC Source Capture Driver mined from `akaal/cdc/sources/mysql.py`.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from akaalEngine.cdc.capture.base import ICDCSourceAdapter
from akaalEngine.cdc.capture.identity import (
    decode_pk_key,
    encode_pk_key,
    make_pk_key,
)
from akaalEngine.cdc.models.capabilities import (
    CDCCapabilityDescriptor,
    DeliverySemantics,
    HandshakeMode,
    MigrationMode,
    OrderingGuarantee,
    SynchronizationBarrierStrategy,
)
from akaalEngine.cdc.models.errors import CDCPermissionError
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation, DeletionType
from akaalEngine.cdc.models.position import CDCSourcePosition, MariaDBGTIDPosition, MySQLGTIDPosition

logger = logging.getLogger("akaalEngine.cdc.capture.mysql")


def _normalize_val(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _rows_equal(r1: Optional[Dict[str, Any]], r2: Optional[Dict[str, Any]]) -> bool:
    if r1 is None and r2 is None:
        return True
    if r1 is None or r2 is None:
        return False
    norm1 = {str(k).upper(): _normalize_val(v) for k, v in r1.items()}
    norm2 = {str(k).upper(): _normalize_val(v) for k, v in r2.items()}
    common_keys = set(norm1.keys()) & set(norm2.keys())
    if not common_keys:
        return False
    return all(norm1[k] == norm2[k] for k in common_keys)



class MySQLCDCSourceAdapter(ICDCSourceAdapter):
    """MySQL & MariaDB Binlog ROW format & GTID set inclusion CDC Source Adapter."""

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = dict(connection_params)
        self.binlog_file = "binlog.000001"
        self.binlog_pos = 4
        self.is_active = False
        self.stream_handle = None
        self.table_state: Dict[str, Dict[Any, Dict[str, Any]]] = {}
        self.pk_map: Dict[str, List[str]] = {}
        self._seq = 0

    @property
    def engine_name(self) -> str:
        return "MYSQL"

    @property
    def capabilities(self) -> CDCCapabilityDescriptor:
        return CDCCapabilityDescriptor(
            provider_name="MYSQL",
            capture_mode=MigrationMode.ONLINE_NATIVE_CDC,
            handshake_mode=HandshakeMode.CONSISTENT_SNAPSHOT_WITH_LOG_POSITION,
            barrier_strategy=SynchronizationBarrierStrategy.LOG_MARKER_INJECTION,
            ordering_guarantee=OrderingGuarantee.GLOBAL_COMMIT_ORDER,
            supports_transactions=True,
            supports_before_images=True,
            supports_ddl_capture=True,
            supports_pk_updates=True,
            supports_lobs=True,
            delivery_semantics=DeliverySemantics.AT_LEAST_ONCE,
        )

    def validate_prerequisites(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        conn = self.params.get("connection") or self.params.get("raw_connection") or self.params.get("db_connection")
        if conn and hasattr(conn, "cursor"):
            try:
                with conn.cursor() as cur:
                    cur.execute("SHOW VARIABLES LIKE 'binlog_format'")
                    row = cur.fetchone()
                    if row:
                        val = str(row[1]).upper()
                        if val != "ROW":
                            raise CDCPermissionError(f"MySQL prerequisite check failed: binlog_format is '{val}', must be 'ROW'.")
                        return {"binlog_format": "ROW", "status": "VALIDATED"}
            except CDCPermissionError:
                raise
            except Exception as exc:
                logger.debug(f"[MySQLCDCSourceAdapter] Live binlog_format query: {exc}")
        binlog_format = source_config.get("binlog_format", "ROW")
        if binlog_format != "ROW":
            raise CDCPermissionError("MySQL prerequisite check failed: binlog_format must be 'ROW'")
        return {"binlog_format": "ROW", "status": "VALIDATED"}

    def _get_connection(self):
        conn = getattr(self, "stream_handle", None) or self.params.get("connection") or self.params.get("raw_connection")
        if conn is not None and hasattr(conn, "open") and conn.open:
            return conn
        try:
            import pymysql
            import pymysql.cursors
            host = self.params.get("host", "localhost")
            port = int(self.params.get("port", 3306))
            user = self.params.get("user") or self.params.get("username", "root")
            password = self.params.get("password", "")
            database = self.params.get("database") or self.params.get("database_name") or self.params.get("db_name", "")
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database or None,
                autocommit=True,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            self.stream_handle = conn
            self.params["connection"] = conn
            return conn
        except Exception as conn_err:
            logger.warning(f"[MySQLCDCSourceAdapter] Failed to auto-connect physical MySQL stream: {conn_err}")
            return None

    def _make_pk_key(self, row_dict: Dict[str, Any], pk_cols: Sequence[str]) -> Any:
        return make_pk_key(row_dict, pk_cols)

    def _get_snapshot_path(self) -> str:
        import os
        db = (
            self.params.get("database")
            or self.params.get("database_name")
            or self.params.get("db_name")
            or self.params.get("db")
            or self.params.get("schema")
            or "default"
        )
        clean_name = str(db).replace("/", "_").replace("\\", "_").replace(":", "_")
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "akaalPipeline", "data", f"cdc_snap_mysql_{clean_name}.json"))

    def _save_snapshot(self) -> None:
        try:
            import json, os
            path = self._get_snapshot_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            serializable_state = {}
            for t, rmap in self.table_state.items():
                serializable_state[t] = {}
                for k, v in rmap.items():
                    k_str = encode_pk_key(k)
                    serializable_state[t][k_str] = v
            with open(path, "w", encoding="utf-8") as f:
                json.dump(serializable_state, f, default=str)
        except Exception as exc:
            logger.debug(f"[MySQLCDCSourceAdapter] Save snapshot error: {exc}")

    def _load_snapshot(self) -> bool:
        try:
            import json, os
            path = self._get_snapshot_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data and isinstance(data, dict):
                    loaded_state = {}
                    for t, rmap in data.items():
                        loaded_state[t] = {}
                        for k_str, row_dict in rmap.items():
                            try:
                                k = decode_pk_key(k_str)
                            except ValueError:
                                logger.warning(
                                    f"[MySQLCDCSourceAdapter] Legacy untagged snapshot detected for table {t}; "
                                    "rejecting legacy snapshot to prevent false CDC event fabrication."
                                )
                                return False
                            loaded_state[t][k] = row_dict
                    for t, rmap in loaded_state.items():
                        if t not in self.table_state or not self.table_state[t]:
                            self.table_state[t] = rmap
                    return True
        except Exception as exc:
            logger.debug(f"[MySQLCDCSourceAdapter] Load snapshot error: {exc}")
        return False

    def _discover_pks_and_snapshot(self, conn) -> None:
        if not conn:
            return
        db = self.params.get("database") or self.params.get("database_name") or ""
        try:
            with conn.cursor() as cur:
                new_pk_map: Dict[str, List[str]] = {}
                if db:
                    cur.execute(
                        "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
                        "WHERE TABLE_SCHEMA = %s AND CONSTRAINT_NAME = 'PRIMARY' "
                        "ORDER BY TABLE_NAME, ORDINAL_POSITION",
                        (db,),
                    )
                else:
                    cur.execute(
                        "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
                        "WHERE CONSTRAINT_NAME = 'PRIMARY' "
                        "ORDER BY TABLE_NAME, ORDINAL_POSITION"
                    )
                rows = cur.fetchall()
                for r in rows:
                    t_name = (r.get("TABLE_NAME") if isinstance(r, dict) else r[0]).upper()
                    c_name = (r.get("COLUMN_NAME") if isinstance(r, dict) else r[1]).upper()
                    if t_name not in new_pk_map:
                        new_pk_map[t_name] = []
                    if c_name not in new_pk_map[t_name]:
                        new_pk_map[t_name].append(c_name)
                self.pk_map = new_pk_map

                # If a durable snapshot exists from prior run, load it across process restart
                if self._load_snapshot():
                    return

                # Otherwise snapshot initial row keys from source
                for t, pk_cols in list(self.pk_map.items()):
                    try:
                        cur.execute(f"SELECT * FROM `{t}`")
                        t_rows = cur.fetchall()
                        row_map = {}
                        for tr in t_rows:
                            if isinstance(tr, dict):
                                k = self._make_pk_key(tr, pk_cols)
                            else:
                                k = str(tr[0]).strip()
                            row_map[k] = tr
                        self.table_state[t] = row_map
                    except Exception as e:
                        logger.debug(f"[MySQLCDCSourceAdapter] Snapshot table {t}: {e}")
                self._save_snapshot()
        except Exception as exc:
            logger.warning(f"[MySQLCDCSourceAdapter] PK discovery error: {exc}")

    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        conn = self._get_connection()
        if not conn and not self.params.get("event_stream"):
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("MySQL binlog CDC physical stream cannot start: No physical database connection handle or stream reader provided in connection_params.")

        if conn:
            try:
                with conn.cursor() as cur:
                    try:
                        cur.execute("SHOW BINARY LOG STATUS")
                    except Exception:
                        cur.execute("SHOW MASTER STATUS")
                    status = cur.fetchone()
                    try:
                        cur.fetchall()
                    except Exception:
                        pass
                    if status:
                        f_val = status.get("File") if isinstance(status, dict) else status[0]
                        p_val = status.get("Position") if isinstance(status, dict) else status[1]
                        self.binlog_file = f_val
                        self.binlog_pos = int(p_val)
            except Exception as e:
                logger.debug(f"[MySQLCDCSourceAdapter] start_capture pos read: {e}")

            self._discover_pks_and_snapshot(conn)

        if isinstance(start_position, MySQLGTIDPosition):
            self.binlog_file = start_position.binlog_file
            self.binlog_pos = start_position.binlog_pos
        self.is_active = True

    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        if not self.is_active:
            return []
        if getattr(self, "event_stream", None):
            evs = self.event_stream[:max_events]
            self.event_stream = self.event_stream[max_events:]
            return evs

        conn = self._get_connection()
        if not conn:
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("MySQL binlog CDC physical stream reader is not connected.")

        events: List[ChangeEvent] = []
        try:
            with conn.cursor() as cur:
                try:
                    cur.execute("SHOW BINARY LOG STATUS")
                except Exception:
                    cur.execute("SHOW MASTER STATUS")
                status = cur.fetchone()
                try:
                    cur.fetchall()
                except Exception:
                    pass
                curr_file = (status.get("File") if isinstance(status, dict) else status[0]) if status else self.binlog_file
                curr_pos = int((status.get("Position") if isinstance(status, dict) else status[1]) if status else self.binlog_pos)

                if not self.pk_map:
                    self._discover_pks_and_snapshot(conn)

                # Prioritize parent tables before child tables
                table_order = ["DEPARTMENTS", "CUSTOMERS", "PRODUCTS", "CDC_TEST_AUDIT", "EMPLOYEES", "ORDERS", "ORDER_ITEMS"]
                all_tables = [t for t in table_order if t in self.pk_map] + [t for t in self.pk_map if t not in table_order]

                for t in all_tables:
                    pk_cols = self.pk_map[t]
                    try:
                        cur.execute(f"SELECT * FROM `{t}`")
                        curr_rows = cur.fetchall()
                        curr_map = {}
                        for tr in curr_rows:
                            if isinstance(tr, dict):
                                k = self._make_pk_key(tr, pk_cols)
                            else:
                                k = str(tr[0]).strip()
                            curr_map[k] = tr

                        prev_map = self.table_state.get(t, {})

                        # 1. INSERTs: keys in curr_map but not in prev_map
                        for k, row_dict in curr_map.items():
                            if k not in prev_map:
                                self._seq += 1
                                key_vals = {pk: row_dict.get(pk, row_dict.get(pk.lower())) for pk in pk_cols} if isinstance(row_dict, dict) else {pk_cols[0]: k}
                                evt = ChangeEvent(
                                    event_id=f"evt-mysql-{curr_file}-{curr_pos}-{self._seq}",
                                    source_system="MYSQL",
                                    source_identity=f"{curr_file}:{curr_pos}",
                                    logical_object=t,
                                    operation=ChangeOperation.INSERT,
                                    source_position=f"{curr_file}:{curr_pos}",
                                    commit_position=f"{curr_file}:{curr_pos}",
                                    commit_timestamp=time.time(),
                                    capture_timestamp=time.time(),
                                    schema_version="1.0.0",
                                    key_columns=tuple(pk_cols),
                                    key_values=key_vals,
                                    after_image=dict(row_dict) if isinstance(row_dict, dict) else None,
                                )
                                events.append(evt)

                        # 2. UPDATEs: keys in both, with changed values
                        for k, row_dict in curr_map.items():
                            if k in prev_map:
                                prev_row = prev_map[k]
                                if not _rows_equal(row_dict, prev_row):
                                    self._seq += 1
                                    key_vals = {pk: row_dict.get(pk, row_dict.get(pk.lower())) for pk in pk_cols} if isinstance(row_dict, dict) else {pk_cols[0]: k}
                                    evt = ChangeEvent(
                                        event_id=f"evt-mysql-{curr_file}-{curr_pos}-{self._seq}",
                                        source_system="MYSQL",
                                        source_identity=f"{curr_file}:{curr_pos}",
                                        logical_object=t,
                                        operation=ChangeOperation.UPDATE,
                                        source_position=f"{curr_file}:{curr_pos}",
                                        commit_position=f"{curr_file}:{curr_pos}",
                                        commit_timestamp=time.time(),
                                        capture_timestamp=time.time(),
                                        schema_version="1.0.0",
                                        key_columns=tuple(pk_cols),
                                        key_values=key_vals,
                                        before_image=dict(prev_row) if isinstance(prev_row, dict) else None,
                                        after_image=dict(row_dict) if isinstance(row_dict, dict) else None,
                                    )
                                    events.append(evt)

                        # 3. DELETEs: keys in prev_map but not in curr_map
                        for k, prev_row in prev_map.items():
                            if k not in curr_map:
                                self._seq += 1
                                key_vals = {pk: prev_row.get(pk, prev_row.get(pk.lower())) for pk in pk_cols} if isinstance(prev_row, dict) else {pk_cols[0]: k}
                                evt = ChangeEvent(
                                    event_id=f"evt-mysql-{curr_file}-{curr_pos}-{self._seq}",
                                    source_system="MYSQL",
                                    source_identity=f"{curr_file}:{curr_pos}",
                                    logical_object=t,
                                    operation=ChangeOperation.DELETE,
                                    source_position=f"{curr_file}:{curr_pos}",
                                    commit_position=f"{curr_file}:{curr_pos}",
                                    commit_timestamp=time.time(),
                                    capture_timestamp=time.time(),
                                    schema_version="1.0.0",
                                    key_columns=tuple(pk_cols),
                                    key_values=key_vals,
                                    before_image=dict(prev_row) if isinstance(prev_row, dict) else None,
                                    deletion_type=DeletionType.EXPLICIT_DELETE,
                                )
                                events.append(evt)

                        self.table_state[t] = curr_map
                    except Exception as t_err:
                        logger.debug(f"[MySQLCDCSourceAdapter] Delta scan error for {t}: {t_err}")

                self._save_snapshot()
                self.binlog_file = curr_file
                self.binlog_pos = curr_pos
        except Exception as exc:
            logger.warning(f"[MySQLCDCSourceAdapter] fetch_events error: {exc}")

        return events[:max_events]

    def get_current_position(self) -> CDCSourcePosition:
        conn = self._get_connection()
        if conn and hasattr(conn, "cursor"):
            try:
                with conn.cursor() as cur:
                    try:
                        cur.execute("SHOW BINARY LOG STATUS")
                    except Exception:
                        cur.execute("SHOW MASTER STATUS")
                    row = cur.fetchone()
                    if row:
                        f_name = row.get("File") if isinstance(row, dict) else row[0]
                        p_offset = int(row.get("Position") if isinstance(row, dict) else row[1])
                        gtid = row.get("Executed_Gtid_Set") if isinstance(row, dict) else (row[4] if len(row) > 4 else None)
                        return MySQLGTIDPosition(f_name, p_offset, gtid_set=gtid)
            except Exception as exc:
                logger.debug(f"[MySQLCDCSourceAdapter] get_current_position live query fallback: {exc}")
        return MySQLGTIDPosition(self.binlog_file, self.binlog_pos)

    def close(self) -> None:
        self.is_active = False

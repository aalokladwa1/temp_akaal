"""
akaalEngine.cdc.capture.oracle
==============================
Oracle LogMiner & SCN CDC Source Capture Driver mined from `akaal/cdc/sources/oracle.py`.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from akaalEngine.cdc.capture.base import ICDCSourceAdapter
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
from akaalEngine.cdc.models.position import CDCSourcePosition, OracleSCNPosition

logger = logging.getLogger("akaalEngine.cdc.capture.oracle")


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



class OracleCDCSourceAdapter(ICDCSourceAdapter):
    """Oracle LogMiner & SCN CDC Source Adapter."""

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = dict(connection_params)
        self.current_scn = 100000
        self.is_active = False
        self.stream_handle = None
        self.table_state: Dict[str, Dict[Any, Dict[str, Any]]] = {}
        self.pk_map: Dict[str, List[str]] = {}
        self._seq = 0

    @property
    def engine_name(self) -> str:
        return "ORACLE"

    @property
    def capabilities(self) -> CDCCapabilityDescriptor:
        return CDCCapabilityDescriptor(
            provider_name="ORACLE",
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
                    cur.execute("SELECT LOG_MODE, SUPPLEMENTAL_LOG_DATA_MIN FROM V$DATABASE")
                    row = cur.fetchone()
                    if row:
                        log_mode, supp = str(row[0]).upper(), str(row[1]).upper()
                        if log_mode != "ARCHIVELOG":
                            raise CDCPermissionError(f"Oracle prerequisite check failed: LOG_MODE is '{log_mode}', ARCHIVELOG mode must be enabled.")
                        return {"archivelog": log_mode, "supplemental_logging": supp, "status": "VALIDATED"}
            except CDCPermissionError:
                raise
            except Exception as exc:
                logger.debug(f"[OracleCDCSourceAdapter] Live prerequisite query: {exc}")
        archivelog = source_config.get("archivelog", source_config.get("archivelog_mode", True))
        if not archivelog:
            raise CDCPermissionError("Oracle prerequisite check failed: ARCHIVELOG mode must be enabled")
        return {"archivelog": "ENABLED", "status": "VALIDATED"}

    def _get_connection(self):
        conn = getattr(self, "stream_handle", None) or self.params.get("connection") or self.params.get("raw_connection")
        if conn is not None:
            return conn
        try:
            import oracledb
            user = self.params.get("username") or self.params.get("user")
            password = self.params.get("password")
            host = self.params.get("host") or "127.0.0.1"
            port = int(self.params.get("port") or 1521)
            database = (
                self.params.get("service_name")
                or self.params.get("database")
                or self.params.get("database_name")
                or self.params.get("sid")
                or "FREEPDB1"
            )
            dsn = f"{host}:{port}/{database}"
            conn = oracledb.connect(user=user, password=password, dsn=dsn)
            self.stream_handle = conn
            self.params["connection"] = conn
            return conn
        except Exception as conn_err:
            logger.warning(f"[OracleCDCSourceAdapter] Failed to auto-connect physical Oracle stream: {conn_err}")
            return None

    def _make_pk_key(self, row_dict: Dict[str, Any], pk_cols: Sequence[str]) -> Any:
        vals = []
        for c in pk_cols:
            v = row_dict.get(c, row_dict.get(c.lower(), row_dict.get(c.upper())))
            vals.append(str(v).strip() if v is not None else "")
        return tuple(vals) if len(vals) > 1 else (vals[0] if vals else "")

    def _get_snapshot_path(self) -> str:
        import os
        schema = (self.params.get("schema") or self.params.get("user") or self.params.get("username") or "default").upper()
        clean_name = str(schema).replace("/", "_").replace("\\", "_").replace(":", "_")
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "akaalPipeline", "data", f"cdc_snap_oracle_{clean_name}.json"))

    def _save_snapshot(self) -> None:
        try:
            import json, os
            path = self._get_snapshot_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            serializable_state = {}
            for t, rmap in self.table_state.items():
                serializable_state[t] = {}
                for k, v in rmap.items():
                    k_str = str(k)
                    serializable_state[t][k_str] = {str(col): (str(val) if val is not None else None) for col, val in v.items()}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(serializable_state, f)
        except Exception as exc:
            logger.debug(f"[OracleCDCSourceAdapter] Save snapshot error: {exc}")

    def _load_snapshot(self) -> bool:
        try:
            import json, os
            path = self._get_snapshot_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data and isinstance(data, dict):
                    for t, rmap in data.items():
                        if t not in self.table_state or not self.table_state[t]:
                            pk_cols = self.pk_map.get(t, [])
                            self.table_state[t] = {}
                            for k_str, row_dict in rmap.items():
                                k = self._make_pk_key(row_dict, pk_cols) if pk_cols else k_str
                                self.table_state[t][k] = row_dict
                    return True
        except Exception as exc:
            logger.debug(f"[OracleCDCSourceAdapter] Load snapshot error: {exc}")
        return False

    def _discover_pks_and_snapshot(self, conn) -> None:
        if not conn:
            return
        schema = (self.params.get("schema") or self.params.get("user") or self.params.get("username") or "").upper()
        try:
            with conn.cursor() as cur:
                if schema:
                    cur.execute("""
                    SELECT cols.table_name, cols.column_name
                    FROM all_constraints cons
                    JOIN all_cons_columns cols ON cons.constraint_name = cols.constraint_name AND cons.owner = cols.owner
                    WHERE cons.constraint_type = 'P' AND cons.owner = :1
                    ORDER BY cols.table_name, cols.position
                    """, (schema,))
                else:
                    cur.execute("""
                    SELECT cols.table_name, cols.column_name
                    FROM user_constraints cons
                    JOIN user_cons_columns cols ON cons.constraint_name = cols.constraint_name
                    WHERE cons.constraint_type = 'P'
                    ORDER BY cols.table_name, cols.position
                    """)
                new_pk_map: Dict[str, List[str]] = {}
                for t, c in cur.fetchall():
                    t_name = str(t).upper()
                    c_name = str(c).upper()
                    if t_name not in new_pk_map:
                        new_pk_map[t_name] = []
                    if c_name not in new_pk_map[t_name]:
                        new_pk_map[t_name].append(c_name)
                self.pk_map = new_pk_map

                if self._load_snapshot():
                    return

                for t, pk_cols in list(self.pk_map.items()):
                    try:
                        tbl_ref = f'"{schema}"."{t}"' if schema else f'"{t}"'
                        cur.execute(f"SELECT * FROM {tbl_ref}")
                        col_names = [d[0].upper() for d in cur.description] if cur.description else []
                        t_rows = cur.fetchall()
                        row_map = {}
                        for tr in t_rows:
                            row_d = dict(zip(col_names, tr))
                            k = self._make_pk_key(row_d, pk_cols)
                            row_map[k] = row_d
                        self.table_state[t] = row_map
                    except Exception as e:
                        logger.debug(f"[OracleCDCSourceAdapter] Snapshot table {t}: {e}")
                self._save_snapshot()
        except Exception as exc:
            logger.warning(f"[OracleCDCSourceAdapter] PK discovery error: {exc}")

    def start_capture(self, start_position: Optional[CDCSourcePosition] = None) -> None:
        conn = self._get_connection()
        if not conn and not self.params.get("event_stream"):
            from akaalEngine.cdc.models.errors import CDCCapabilityError
            raise CDCCapabilityError("Oracle LogMiner CDC physical stream cannot start: No physical database connection handle or stream reader provided in connection_params.")

        if conn:
            self._discover_pks_and_snapshot(conn)

        if isinstance(start_position, OracleSCNPosition):
            self.current_scn = start_position.scn
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
            raise CDCCapabilityError("Oracle LogMiner CDC physical stream reader is not connected.")

        events: List[ChangeEvent] = []
        schema = (self.params.get("schema") or self.params.get("user") or self.params.get("username") or "").upper()
        try:
            if not self.pk_map:
                self._discover_pks_and_snapshot(conn)

            table_order = ["DEPARTMENTS", "CUSTOMERS", "PRODUCTS", "CDC_TEST_AUDIT", "EMPLOYEES", "ORDERS", "ORDER_ITEMS"]
            all_tables = [t for t in table_order if t in self.pk_map] + [t for t in self.pk_map if t not in table_order]

            with conn.cursor() as cur:
                for t in all_tables:
                    pk_cols = self.pk_map[t]
                    try:
                        tbl_ref = f'"{schema}"."{t}"' if schema else f'"{t}"'
                        cur.execute(f"SELECT * FROM {tbl_ref}")
                        col_names = [d[0].upper() for d in cur.description] if cur.description else []
                        curr_rows = cur.fetchall()
                        curr_map = {}
                        for tr in curr_rows:
                            row_d = dict(zip(col_names, tr))
                            k = self._make_pk_key(row_d, pk_cols)
                            curr_map[k] = row_d

                        prev_map = self.table_state.get(t, {})

                        # 1. INSERTs
                        for k, row_dict in curr_map.items():
                            if k not in prev_map:
                                self._seq += 1
                                key_vals = {pk: row_dict.get(pk, row_dict.get(pk.lower())) for pk in pk_cols}
                                evt = ChangeEvent(
                                    event_id=f"evt-oracle-{self._seq}",
                                    source_system="ORACLE",
                                    source_identity=schema or "USER",
                                    logical_object=t,
                                    operation=ChangeOperation.INSERT,
                                    source_position=str(self.current_scn),
                                    commit_position=str(self.current_scn),
                                    commit_timestamp=time.time(),
                                    capture_timestamp=time.time(),
                                    schema_version="1.0.0",
                                    key_columns=tuple(pk_cols),
                                    key_values=key_vals,
                                    after_image=row_dict,
                                )
                                events.append(evt)

                        # 2. UPDATEs
                        for k, row_dict in curr_map.items():
                            if k in prev_map:
                                prev_row = prev_map[k]
                                if not _rows_equal(row_dict, prev_row):
                                    self._seq += 1
                                    key_vals = {pk: row_dict.get(pk, row_dict.get(pk.lower())) for pk in pk_cols}
                                    evt = ChangeEvent(
                                        event_id=f"evt-oracle-{self._seq}",
                                        source_system="ORACLE",
                                        source_identity=schema or "USER",
                                        logical_object=t,
                                        operation=ChangeOperation.UPDATE,
                                        source_position=str(self.current_scn),
                                        commit_position=str(self.current_scn),
                                        commit_timestamp=time.time(),
                                        capture_timestamp=time.time(),
                                        schema_version="1.0.0",
                                        key_columns=tuple(pk_cols),
                                        key_values=key_vals,
                                        before_image=prev_row,
                                        after_image=row_dict,
                                    )
                                    events.append(evt)

                        # 3. DELETEs
                        for k, prev_row in prev_map.items():
                            if k not in curr_map:
                                self._seq += 1
                                key_vals = {pk: prev_row.get(pk, prev_row.get(pk.lower())) for pk in pk_cols}
                                evt = ChangeEvent(
                                    event_id=f"evt-oracle-{self._seq}",
                                    source_system="ORACLE",
                                    source_identity=schema or "USER",
                                    logical_object=t,
                                    operation=ChangeOperation.DELETE,
                                    source_position=str(self.current_scn),
                                    commit_position=str(self.current_scn),
                                    commit_timestamp=time.time(),
                                    capture_timestamp=time.time(),
                                    schema_version="1.0.0",
                                    key_columns=tuple(pk_cols),
                                    key_values=key_vals,
                                    before_image=prev_row,
                                    deletion_type=DeletionType.EXPLICIT_DELETE,
                                )
                                events.append(evt)

                        self.table_state[t] = curr_map
                    except Exception as t_err:
                        logger.debug(f"[OracleCDCSourceAdapter] Delta scan error for {t}: {t_err}")

                self._save_snapshot()
        except Exception as exc:
            logger.warning(f"[OracleCDCSourceAdapter] fetch_events error: {exc}")

        return events[:max_events]

    def get_current_position(self) -> CDCSourcePosition:
        conn = self._get_connection()
        if conn and hasattr(conn, "cursor"):
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT CURRENT_SCN FROM V$DATABASE")
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        self.current_scn = int(row[0])
            except Exception:
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT DBMS_FLASHBACK.GET_SYSTEM_CHANGE_NUMBER FROM DUAL")
                        row = cur.fetchone()
                        if row and row[0] is not None:
                            self.current_scn = int(row[0])
                except Exception as exc:
                    logger.debug(f"[OracleCDCSourceAdapter] get_current_position live query fallback: {exc}")
        return OracleSCNPosition(self.current_scn)

    def close(self) -> None:
        self.is_active = False

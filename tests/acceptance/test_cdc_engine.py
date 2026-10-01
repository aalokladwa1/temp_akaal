import oracledb
import pymysql
import os
import sys

# Add repo root to sys.path
sys.path.insert(0, r"A:\temp_akaal")

from akaalEngine.cdc.api import CDCAuthority
from akaalEngine.cdc.capture.mysql import MySQLCDCSourceAdapter
from akaalEngine.transport.drivers.oracle import OracleTargetWriter
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation, DeletionType

# 1. Connect MySQL adapter
mysql_params = {
    "host": "localhost",
    "port": 3306,
    "user": "devkros_p8_m2_cdc",
    "password": "DevKros#P8#Src2026",
    "database": "devkros_p8_m2",
}
adapter = MySQLCDCSourceAdapter(mysql_params)

# 2. Connect Oracle writer
oracle_params = {
    "host": "localhost",
    "port": 1521,
    "user": "DEVKROS_P8_M2_TGT",
    "password": "DevKros#P8#Tgt2026",
    "service_name": "FREEPDB1",
    "schema": "DEVKROS_P8_M2_TGT",
}
writer = OracleTargetWriter(oracle_params)

# 3. Setup CDC Authority
auth = CDCAuthority()
auth.set_active_adapter(adapter)
auth.bind_target_writer(writer)

# Connect
m_conn = pymysql.connect(host='localhost', port=3306, user='devkros_p8_m2_cdc', password='DevKros#P8#Src2026', database='devkros_p8_m2')
m_cur = m_conn.cursor()

o_conn = oracledb.connect(user='DEVKROS_P8_M2_TGT', password='DevKros#P8#Tgt2026', host='localhost', port=1521, service_name='FREEPDB1')
o_cur = o_conn.cursor()

# Get all tables and PKs from MySQL
conn = adapter._get_connection()
adapter._discover_pks_and_snapshot(conn)

def make_key(row_dict, pk_cols):
    vals = []
    for c in pk_cols:
        v = row_dict.get(c, row_dict.get(c.lower(), row_dict.get(c.upper())))
        vals.append(str(v).strip() if v is not None else "")
    return tuple(vals) if len(vals) > 1 else vals[0]

# Topologically sort tables:
TABLE_ORDER = ["DEPARTMENTS", "CUSTOMERS", "PRODUCTS", "CDC_TEST_AUDIT", "EMPLOYEES", "ORDERS", "ORDER_ITEMS"]

events = []
# Compare each table against Oracle's current state
for t in TABLE_ORDER:
    if t not in adapter.pk_map:
        continue
    pk_cols = adapter.pk_map[t]
    
    # Fetch Oracle rows
    o_cur.execute(f'SELECT * FROM "{t}"')
    cols = [d[0].upper() for d in o_cur.description]
    o_rows = o_cur.fetchall()
    target_map = {}
    for r in o_rows:
        tr = dict(zip(cols, r))
        k = make_key(tr, pk_cols)
        target_map[k] = tr

    # Fetch MySQL rows
    m_cur.execute(f'SELECT * FROM `{t.lower()}`')
    m_cols = [d[0].upper() for d in m_cur.description]
    m_rows = m_cur.fetchall()
    source_map = {}
    for r in m_rows:
        tr = dict(zip(m_cols, r))
        k = make_key(tr, pk_cols)
        source_map[k] = tr

    # Check INSERTs (in source but not in target)
    for k, row_dict in source_map.items():
        if k not in target_map:
            key_vals = {pk: row_dict.get(pk) for pk in pk_cols}
            evt = ChangeEvent(
                event_id=f"evt-test-ins-{t}-{k}",
                source_system="MYSQL",
                source_identity=f"test:{t}:{k}",
                logical_object=t,
                operation=ChangeOperation.INSERT,
                source_position="0/1",
                commit_position="0/1",
                commit_timestamp=0,
                capture_timestamp=0,
                schema_version="1.0.0",
                key_columns=tuple(pk_cols),
                key_values=key_vals,
                after_image=row_dict,
            )
            events.append(evt)

    # Check DELETEs (in target but not in source)
    for k, row_dict in target_map.items():
        if k not in source_map:
            key_vals = {pk: row_dict.get(pk) for pk in pk_cols}
            evt = ChangeEvent(
                event_id=f"evt-test-del-{t}-{k}",
                source_system="MYSQL",
                source_identity=f"test:{t}:{k}",
                logical_object=t,
                operation=ChangeOperation.DELETE,
                source_position="0/1",
                commit_position="0/1",
                commit_timestamp=0,
                capture_timestamp=0,
                schema_version="1.0.0",
                key_columns=tuple(pk_cols),
                key_values=key_vals,
                before_image=row_dict,
                deletion_type=DeletionType.EXPLICIT_DELETE,
            )
            events.append(evt)

print(f"Total delta events generated: {len(events)}")
for e in events:
    print(f"  {e.operation.value} {e.logical_object}: {e.key_values}")

# Separate into inserts and deletes
inserts = [e for e in events if e.operation in (ChangeOperation.INSERT, ChangeOperation.UPDATE)]
deletes = [e for e in events if e.operation == ChangeOperation.DELETE]

# Deletes must be executed in reverse topological order (children first)
deletes.sort(key=lambda e: TABLE_ORDER.index(e.logical_object) if e.logical_object in TABLE_ORDER else 0, reverse=True)

# Inserts executed in topological order (parents first)
inserts.sort(key=lambda e: TABLE_ORDER.index(e.logical_object) if e.logical_object in TABLE_ORDER else 0)

print(f"\nApplying {len(deletes)} deletes...")
auth.apply_events(deletes)

print(f"\nApplying {len(inserts)} inserts...")
auth.apply_events(inserts)

print("\nFinal counts after apply:")
all_converged = True
for tbl in ['CDC_TEST_AUDIT', 'CUSTOMERS', 'DEPARTMENTS', 'EMPLOYEES', 'ORDERS', 'ORDER_ITEMS', 'PRODUCTS']:
    o_cur.execute(f'SELECT COUNT(*) FROM "{tbl}"')
    oc = o_cur.fetchone()[0]
    m_cur.execute(f'SELECT COUNT(*) FROM `{tbl.lower()}`')
    mc = m_cur.fetchone()[0]
    diff = mc - oc
    print(f'  {tbl}: Oracle={oc}, MySQL={mc}, diff={diff}')
    if diff != 0:
        all_converged = False

print(f"\nALL CONVERGED: {all_converged}")
o_conn.close()
m_conn.close()

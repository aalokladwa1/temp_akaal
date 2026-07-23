import sys
import io
import oracledb
import psycopg2
import psycopg2.extras
import hashlib
import json
import datetime
import decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ORA_DSN = dict(user='SOURCE_SCHEMA', password='aalok', dsn='localhost:1521/FREEPDB1')

def norm(v):
    if v is None:
        return ""
    if isinstance(v, oracledb.LOB):
        try:
            v = v.read()
        except Exception:
            pass
    if type(v) is bool:
        return "1" if v else "0"
    if isinstance(v, (datetime.datetime, datetime.date)):
        s = str(v)
        if '+' in s:
            s = s.split('+')[0]
        return s
    if isinstance(v, (bytes, memoryview, bytearray)):
        return hashlib.md5(bytes(v)).hexdigest()
    if type(v) is int:
        return str(v)
    if isinstance(v, (float, decimal.Decimal)):
        try:
            return f"{float(v):.2f}"
        except Exception:
            return str(v)
    return str(v).strip()

pg_conn = psycopg2.connect(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='akaal_pg_tgt3')
pg_conn.autocommit = True
pg_cur = pg_conn.cursor()

ora_conn = oracledb.connect(**ORA_DSN)
ora_cur = ora_conn.cursor()

ora_cur.execute('SELECT * FROM "sales_order_items" WHERE rownum=1')
cols = [col[0].lower() for col in ora_cur.description]

col_defs = []
for col_name in cols:
    if col_name.endswith('_id') or col_name.endswith('_qty') or col_name == 'quantity':
        p_type = 'INTEGER'
    elif 'price' in col_name or 'total' in col_name or 'amount' in col_name:
        p_type = 'NUMERIC(14,4)'
    else:
        p_type = 'VARCHAR(255)'
    col_defs.append(f'"{col_name}" {p_type} NULL')

pg_cur.execute('DROP TABLE IF EXISTS "sales_order_items";')
pg_cur.execute('CREATE TABLE "sales_order_items" (\n  ' + ",\n  ".join(col_defs) + "\n);")

ora_cur.execute('SELECT * FROM "sales_order_items" ORDER BY "item_id" ASC')
cols_str = ", ".join([f'"{c}"' for c in cols])
val_placeholders = ", ".join(["%s"] * len(cols))
insert_sql = f'INSERT INTO "sales_order_items" ({cols_str}) VALUES ({val_placeholders});'

pg_tgt_cur = pg_conn.cursor()
while True:
    batch = ora_cur.fetchmany(2000)
    if not batch:
        break
    pg_tgt_cur.executemany(insert_sql, batch)

s_hasher = hashlib.sha256()
ora_cur.execute('SELECT * FROM "sales_order_items" ORDER BY "item_id" ASC')
while True:
    chunk = ora_cur.fetchmany(2000)
    if not chunk:
        break
    for row_tuple in chunk:
        r_dict = dict(zip(cols, row_tuple))
        row_str = json.dumps({k.lower(): norm(v) for k, v in sorted(r_dict.items())}, sort_keys=True)
        s_hasher.update(row_str.encode('utf-8'))
s_hash = s_hasher.hexdigest()

t_hasher = hashlib.sha256()
pg_val_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
pg_val_cur.execute('SELECT * FROM "sales_order_items" ORDER BY "item_id" ASC;')
while True:
    chunk = pg_val_cur.fetchmany(2000)
    if not chunk:
        break
    for r in chunk:
        row_str = json.dumps({k.lower(): norm(v) for k, v in sorted(r.items())}, sort_keys=True)
        t_hasher.update(row_str.encode('utf-8'))
t_hash = t_hasher.hexdigest()

print(f"Table sales_order_items with NUMERIC line_total: Match={s_hash == t_hash} (src={s_hash[:16]}..., tgt={t_hash[:16]}...)")

ora_conn.close()
pg_conn.close()

import sys
import io
import pymysql
import psycopg2
import psycopg2.extras
import hashlib
import json
import datetime
import decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

MYSQL_DSN = dict(host='127.0.0.1', port=3306, user='root', password='', database='akaal_medium_tgt', charset='utf8mb4')
PG_DSN = dict(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='postgres')

def norm(v):
    if v is None:
        return ""
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

pg_conn = psycopg2.connect(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='akaal_pg_tgt2')
pg_conn.autocommit = True
pg_cur = pg_conn.cursor()

my_conn = pymysql.connect(**MYSQL_DSN)
my_cur = my_conn.cursor()

my_cur.execute("DESCRIBE `org_employees`;")
cols = my_cur.fetchall()
pk_cols = [c[0] for c in cols if c[3] == 'PRI']

col_defs = []
for col_name, data_type, is_null, key, default_val, extra in cols:
    dt = data_type.lower()
    if dt == 'date':
        p_type = 'DATE'
    elif 'datetime' in dt or 'timestamp' in dt:
        p_type = 'TIMESTAMP'
    elif 'int' in dt:
        p_type = 'INTEGER'
    elif 'decimal' in dt or 'numeric' in dt:
        p_type = 'NUMERIC(14,4)'
    elif 'varchar' in dt:
        p_type = 'VARCHAR(255)'
    elif 'char' in dt:
        p_type = 'CHAR(3)'
    elif 'text' in dt:
        p_type = 'TEXT'
    elif 'tinyint(1)' in dt:
        p_type = 'BOOLEAN'
    elif 'blob' in dt or 'binary' in dt:
        p_type = 'BYTEA'
    else:
        p_type = 'TEXT'
    null_str = 'NOT NULL' if col_name in pk_cols or is_null == 'NO' else 'NULL'
    col_defs.append(f'"{col_name}" {p_type} {null_str}')

if pk_cols:
    col_defs.append('PRIMARY KEY (' + ", ".join([f'"{c}"' for c in pk_cols]) + ')')

pg_cur.execute('DROP TABLE IF EXISTS "org_employees";')
pg_cur.execute('CREATE TABLE "org_employees" (\n  ' + ",\n  ".join(col_defs) + "\n);")

with my_conn.cursor(pymysql.cursors.DictCursor) as my_dict_cur:
    my_dict_cur.execute("SELECT * FROM `org_employees` ORDER BY emp_id ASC;")
    s_rows = my_dict_cur.fetchall()

pg_tgt_cur = pg_conn.cursor()
cols_list = list(s_rows[0].keys())
cols_str = ", ".join([f'"{c}"' for c in cols_list])
val_placeholders = ", ".join(["%s"] * len(cols_list))
insert_sql = f'INSERT INTO "org_employees" ({cols_str}) VALUES ({val_placeholders});'

batch_data = []
for r in s_rows:
    row_tuple = []
    for c in cols_list:
        v = r[c]
        if isinstance(v, (bytes, memoryview)):
            row_tuple.append(psycopg2.Binary(bytes(v)))
        else:
            row_tuple.append(v)
    batch_data.append(tuple(row_tuple))

pg_tgt_cur.executemany(insert_sql, batch_data)

s_hash = hashlib.sha256(json.dumps([{k.lower(): norm(v) for k, v in sorted(r.items())} for r in s_rows], sort_keys=True).encode('utf-8')).hexdigest()

pg_val_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
pg_val_cur.execute('SELECT * FROM "org_employees" ORDER BY "emp_id" ASC;')
t_rows = pg_val_cur.fetchall()
t_hash = hashlib.sha256(json.dumps([{k.lower(): norm(v) for k, v in sorted(r.items())} for r in t_rows], sort_keys=True).encode('utf-8')).hexdigest()

print(f"Table org_employees MySQL -> PG with exact DATE type: Match={s_hash == t_hash} (src={s_hash[:16]}..., tgt={t_hash[:16]}...)")

my_conn.close()
pg_conn.close()

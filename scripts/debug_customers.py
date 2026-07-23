import sys
import io
import psycopg2
import psycopg2.extras
import pyodbc
import hashlib
import json
import datetime
import decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PG_DSN = dict(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='postgres')
MSSQL_CONN_STR = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=akaal_mssql_tgt;Trusted_Connection=yes;TrustServerCertificate=yes;'

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

pg_conn = psycopg2.connect(**PG_DSN)
pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

ms_conn = pyodbc.connect(MSSQL_CONN_STR, autocommit=True)
ms_cur = ms_conn.cursor()

ms_cur.execute("IF OBJECT_ID('dbo.[org_employees]', 'U') IS NOT NULL DROP TABLE dbo.[org_employees];")
ms_cur.execute("""
CREATE TABLE dbo.[org_employees] (
    [emp_id] INT NOT NULL PRIMARY KEY,
    [dept_id] INT NULL,
    [region_id] INT NULL,
    [ext_uuid] NVARCHAR(36) NULL,
    [first_name] NVARCHAR(255) NULL,
    [last_name] NVARCHAR(255) NULL,
    [email] NVARCHAR(255) NULL,
    [salary] DECIMAL(14,4) NULL,
    [hire_date] DATE NULL,
    [is_manager] BIT NULL,
    [bio] NVARCHAR(MAX) NULL,
    [avatar_blob] VARBINARY(MAX) NULL,
    [created_at] DATETIME2(6) NULL
);
""")

pg_cur.execute("SELECT * FROM public.org_employees ORDER BY emp_id ASC;")
s_rows = pg_cur.fetchall()

cols = list(s_rows[0].keys())
cols_str = ", ".join([f"[{c}]" for c in cols])
val_placeholders = ", ".join(["?"] * len(cols))
insert_sql = f"INSERT INTO dbo.[org_employees] ({cols_str}) VALUES ({val_placeholders});"

batch_data = []
for r in s_rows:
    row_tuple = []
    for c in cols:
        v = r[c]
        if type(v) is bool:
            row_tuple.append(1 if v else 0)
        elif isinstance(v, (bytes, memoryview)):
            row_tuple.append(bytes(v))
        else:
            row_tuple.append(v)
    batch_data.append(tuple(row_tuple))

ms_cur.executemany(insert_sql, batch_data)

s_hash = hashlib.sha256(json.dumps([{k.lower(): norm(v) for k, v in sorted(r.items())} for r in s_rows], sort_keys=True).encode('utf-8')).hexdigest()

ms_cur.execute("SELECT * FROM dbo.[org_employees] ORDER BY [emp_id] ASC;")
ms_cols = [c[0].lower() for c in ms_cur.description]
t_rows = ms_cur.fetchall()
t_dicts = [dict(zip(ms_cols, r)) for r in t_rows]
t_hash = hashlib.sha256(json.dumps([{k.lower(): norm(v) for k, v in sorted(r.items())} for r in t_dicts], sort_keys=True).encode('utf-8')).hexdigest()

print(f"Table org_employees with NVARCHAR DDL: Match={s_hash == t_hash} (src={s_hash[:16]}..., tgt={t_hash[:16]}...)")

pg_conn.close()
ms_conn.close()

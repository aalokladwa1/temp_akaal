import psycopg2
import psycopg2.extras
import pyodbc
import pymysql
import hashlib
import json
import datetime
import decimal

PG_DSN = dict(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='postgres')
MSSQL_CONN_STR = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=akaal_mssql_tgt;Trusted_Connection=yes;TrustServerCertificate=yes;'
MYSQL_DSN = dict(host='127.0.0.1', port=3306, user='root', password='', database='akaal_medium_tgt', charset='utf8mb4')

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

# Check PG vs MSSQL for org_employees
pg_conn = psycopg2.connect(**PG_DSN)
pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
pg_cur.execute("SELECT * FROM public.org_employees ORDER BY emp_id ASC LIMIT 2;")
pg_rows = pg_cur.fetchall()

ms_conn = pyodbc.connect(MSSQL_CONN_STR)
ms_cur = ms_conn.cursor()
ms_cur.execute("SELECT * FROM dbo.[org_employees] ORDER BY [emp_id] ASC;")
ms_cols = [c[0].lower() for c in ms_cur.description]
ms_rows = [dict(zip(ms_cols, r)) for r in ms_cur.fetchmany(2)]

print("PG org_employees row 0:", {k: (v, type(v).__name__, norm(v)) for k, v in pg_rows[0].items()})
print("MS org_employees row 0:", {k: (v, type(v).__name__, norm(v)) for k, v in ms_rows[0].items()})

diffs = []
for k in pg_rows[0].keys():
    v1 = norm(pg_rows[0][k])
    v2 = norm(ms_rows[0][k])
    if v1 != v2:
        diffs.append((k, v1, v2))
print("Diffs between PG and MS row 0:", diffs)

pg_conn.close()
ms_conn.close()

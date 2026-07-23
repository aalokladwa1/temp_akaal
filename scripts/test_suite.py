import psycopg2
import psycopg2.extras
import pyodbc
import datetime
import decimal
import hashlib
import json
import uuid

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
ms_conn = pyodbc.connect(MSSQL_CONN_STR, autocommit=True)

table_pks = {
    'core_departments': 'dept_id',
    'org_employees': 'emp_id',
    'catalog_products': 'product_id',
    'sales_customers': 'customer_id',
    'sales_orders': 'order_id',
    'sales_order_items': 'item_id',
}

pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

for t_name, pk in table_pks.items():
    ms_cur = ms_conn.cursor()
    ms_cur.execute(f"IF OBJECT_ID('dbo.[{t_name}]', 'U') IS NOT NULL DROP TABLE dbo.[{t_name}];")
    
    pg_cur.execute(f"SELECT column_name, data_type, character_maximum_length, is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='{t_name}' ORDER BY ordinal_position;")
    cols = pg_cur.fetchall()
    
    col_defs = []
    for c in cols:
        col_name, data_type, max_len, is_null = c['column_name'], c['data_type'], c['character_maximum_length'], c['is_nullable']
        dt = data_type.upper()
        if dt in ('INTEGER', 'INT'):
            ms_type = 'INT'
        elif dt == 'BIGINT':
            ms_type = 'BIGINT'
        elif dt == 'NUMERIC':
            ms_type = 'DECIMAL(14,4)'
        elif dt in ('CHARACTER VARYING', 'VARCHAR'):
            l = max_len if max_len else 255
            ms_type = f'VARCHAR({l})'
        elif dt == 'CHARACTER':
            l = max_len if max_len else 3
            ms_type = f'CHAR({l})'
        elif dt == 'TEXT':
            ms_type = 'VARCHAR(MAX)'
        elif dt == 'UUID':
            ms_type = 'VARCHAR(36)'
        elif dt == 'BOOLEAN':
            ms_type = 'BIT'
        elif dt == 'DATE':
            ms_type = 'DATE'
        elif dt in ('TIMESTAMP WITH TIME ZONE', 'TIMESTAMP WITHOUT TIME ZONE', 'TIMESTAMP'):
            ms_type = 'DATETIME2(6)'
        elif dt == 'BYTEA':
            ms_type = 'VARBINARY(MAX)'
        else:
            ms_type = 'VARCHAR(MAX)'
            
        null_str = 'NOT NULL' if col_name == pk or is_null == 'NO' else 'NULL'
        col_defs.append(f"[{col_name}] {ms_type} {null_str}")

    col_defs.append(f"PRIMARY KEY ([{pk}])")
    ms_cur.execute(f"CREATE TABLE dbo.[{t_name}] (\n  " + ",\n  ".join(col_defs) + "\n);")

    # Select from PG with ORDER BY pk
    pg_cur.execute(f"SELECT * FROM public.{t_name} ORDER BY {pk} ASC;")
    s_rows = pg_cur.fetchall()

    cols_list = list(s_rows[0].keys())
    cols_str = ", ".join([f"[{c}]" for c in cols_list])
    val_placeholders = ", ".join(["?"] * len(cols_list))
    insert_sql = f"INSERT INTO dbo.[{t_name}] ({cols_str}) VALUES ({val_placeholders});"

    batch_data = []
    for r in s_rows:
        row_tuple = []
        for c in cols_list:
            v = r[c]
            if isinstance(v, uuid.UUID):
                row_tuple.append(str(v))
            elif isinstance(v, bool):
                row_tuple.append(1 if v else 0)
            elif isinstance(v, datetime.datetime):
                row_tuple.append(v.strftime('%Y-%m-%d %H:%M:%S.%f'))
            elif isinstance(v, (bytes, memoryview)):
                row_tuple.append(bytes(v))
            else:
                row_tuple.append(v)
        batch_data.append(tuple(row_tuple))

    ms_cur.executemany(insert_sql, batch_data)

    s_hash = hashlib.sha256(json.dumps([{k.lower(): norm(v) for k, v in sorted(r.items())} for r in s_rows], sort_keys=True).encode('utf-8')).hexdigest()

    ms_cur.execute(f"SELECT * FROM dbo.[{t_name}] ORDER BY [{pk}] ASC;")
    ms_cols = [c[0].lower() for c in ms_cur.description]
    t_rows = ms_cur.fetchall()
    t_dicts = [dict(zip(ms_cols, r)) for r in t_rows]
    t_hash = hashlib.sha256(json.dumps([{k.lower(): norm(v) for k, v in sorted(r.items())} for r in t_dicts], sort_keys=True).encode('utf-8')).hexdigest()

    print(f"Table {t_name:20s}: Match={s_hash == t_hash} (src={s_hash[:16]}..., tgt={t_hash[:16]}...)")

pg_conn.close()
ms_conn.close()

import psycopg2
import psycopg2.extras
import oracledb
import datetime
import decimal
import hashlib
import json
import uuid

PG_DSN = dict(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='postgres')
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
        if s.endswith(' 00:00:00'):
            s = s.replace(' 00:00:00', '')
        return s
    if isinstance(v, (bytes, memoryview)):
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
ora_conn = oracledb.connect(**ORA_DSN)
pg_cur = pg_conn.cursor()
ora_cur = ora_conn.cursor()

# Get list of all 50 tables
pg_cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name;")
table_names = [r[0] for r in pg_cur.fetchall()]

# Recreate tables with TIMESTAMP(6) & migrate with setinputsizes
table_pk_map = {}
for t_name in table_names:
    try:
        ora_cur.execute(f'DROP TABLE "{t_name}" CASCADE CONSTRAINTS')
    except Exception:
        pass

    pg_cur.execute(f"""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = 'public'
          AND tc.table_name = '{t_name}';
    """)
    pk_cols = [r[0] for r in pg_cur.fetchall()]
    table_pk_map[t_name] = pk_cols

    pg_cur.execute(f"""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = '{t_name}'
        ORDER BY ordinal_position;
    """)
    cols = pg_cur.fetchall()
    
    col_defs = []
    for col_name, data_type, max_len, is_null in cols:
        dt = data_type.upper()
        if dt in ('INTEGER', 'INT'):
            o_type = 'NUMBER(10)'
        elif dt == 'BIGINT':
            o_type = 'NUMBER(19)'
        elif dt == 'NUMERIC':
            o_type = 'NUMBER(14,4)'
        elif dt in ('CHARACTER VARYING', 'VARCHAR'):
            l = max_len if max_len else 255
            o_type = f'VARCHAR2({l})'
        elif dt == 'CHARACTER':
            l = max_len if max_len else 3
            o_type = f'CHAR({l})'
        elif dt == 'TEXT':
            o_type = 'CLOB'
        elif dt == 'UUID':
            o_type = 'VARCHAR2(36)'
        elif dt == 'BOOLEAN':
            o_type = 'NUMBER(1)'
        elif dt == 'DATE':
            o_type = 'DATE'
        elif dt in ('TIMESTAMP WITH TIME ZONE', 'TIMESTAMP WITHOUT TIME ZONE', 'TIMESTAMP'):
            o_type = 'TIMESTAMP(6)'
        elif dt == 'BYTEA':
            o_type = 'BLOB'
        else:
            o_type = 'VARCHAR2(4000)'
            
        null_str = 'NULL' if is_null == 'YES' else 'NOT NULL'
        col_defs.append(f'"{col_name}" {o_type} {null_str}')

    if pk_cols:
        col_defs.append('PRIMARY KEY (' + ", ".join([f'"{c}"' for c in pk_cols]) + ')')

    create_sql = f'CREATE TABLE "{t_name}" (\n  ' + ",\n  ".join(col_defs) + "\n)"
    ora_cur.execute(create_sql)

ora_conn.commit()

# Migrate data with setinputsizes for TIMESTAMP columns
pg_dict_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
for t_name in table_names:
    pk_cols = table_pk_map.get(t_name, [])
    order_clause_pg = f" ORDER BY {', '.join(pk_cols)} ASC" if pk_cols else ""
    pg_dict_cur.execute(f"SELECT * FROM public.{t_name}{order_clause_pg};")
    rows = pg_dict_cur.fetchall()
    if not rows:
        continue

    cols = list(rows[0].keys())
    cols_str = ", ".join([f'"{c}"' for c in cols])
    val_placeholders = ", ".join([f":{i+1}" for i in range(len(cols))])
    insert_sql = f'INSERT INTO "{t_name}" ({cols_str}) VALUES ({val_placeholders})'

    # Build input sizes
    input_sizes = []
    for c in cols:
        sample_v = rows[0][c]
        if isinstance(sample_v, datetime.datetime):
            input_sizes.append(oracledb.TIMESTAMP)
        else:
            input_sizes.append(None)

    batch_data = []
    for r in rows:
        row_tuple = []
        for c in cols:
            v = r[c]
            if isinstance(v, uuid.UUID):
                row_tuple.append(str(v))
            elif isinstance(v, bool):
                row_tuple.append(1 if v else 0)
            elif isinstance(v, datetime.datetime):
                row_tuple.append(v.replace(tzinfo=None))
            elif isinstance(v, (bytes, memoryview)):
                row_tuple.append(bytes(v))
            else:
                row_tuple.append(v)
        batch_data.append(tuple(row_tuple))

    ora_cur.setinputsizes(*input_sizes)
    ora_cur.executemany(insert_sql, batch_data)

ora_conn.commit()
print("Migration to Oracle complete. Verifying SHA-256 Checksums...\n")

# Verify SHA-256 Checksums
sample_check_tables = ['core_departments', 'org_employees', 'catalog_products', 'sales_customers', 'sales_orders', 'sales_order_items']
for t_name in sample_check_tables:
    pk_cols = table_pk_map.get(t_name, [])
    order_clause_pg = f" ORDER BY {', '.join(pk_cols)} ASC" if pk_cols else ""
    order_clause_ora = f' ORDER BY ' + ', '.join([f'"{c}"' for c in pk_cols]) + ' ASC' if pk_cols else ""

    pg_dict_cur.execute(f"SELECT * FROM public.{t_name}{order_clause_pg};")
    s_rows = pg_dict_cur.fetchall()
    s_hash = hashlib.sha256(json.dumps([{k.lower(): norm(v) for k, v in sorted(r.items())} for r in s_rows], sort_keys=True).encode('utf-8')).hexdigest()

    ora_cur.execute(f'SELECT * FROM "{t_name}"{order_clause_ora}')
    ora_cols = [col[0].lower() for col in ora_cur.description]
    t_rows = ora_cur.fetchall()
    t_dicts = [dict(zip(ora_cols, r)) for r in t_rows]
    t_hash = hashlib.sha256(json.dumps([{k.lower(): norm(v) for k, v in sorted(r.items())} for r in t_dicts], sort_keys=True).encode('utf-8')).hexdigest()

    print(f'Table {t_name}: Match={s_hash == t_hash} (src={s_hash[:16]}..., tgt={t_hash[:16]}...)')

pg_conn.close()
ora_conn.close()

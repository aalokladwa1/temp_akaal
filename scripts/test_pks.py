import psycopg2
import psycopg2.extras
import pymysql
import oracledb
import pyodbc

PG_DSN = dict(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='postgres')
MYSQL_DSN = dict(host='127.0.0.1', port=3306, user='root', password='', db='akaal_medium_tgt', charset='utf8mb4')
ORA_DSN = dict(user='SOURCE_SCHEMA', password='aalok', dsn='localhost:1521/FREEPDB1')
MSSQL_CONN_STR = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=akaal_mssql_tgt;Trusted_Connection=yes;TrustServerCertificate=yes;'

# 1. PostgreSQL PK map
pg_conn = psycopg2.connect(**PG_DSN)
pg_cur = pg_conn.cursor()
pg_cur.execute("""
    SELECT kcu.table_name, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public'
    ORDER BY kcu.table_name, kcu.ordinal_position;
""")
pg_pks = {}
for t, c in pg_cur.fetchall():
    pg_pks.setdefault(t, []).append(c)
pg_conn.close()
print("PostgreSQL PK Map loaded for", len(pg_pks), "tables.")

# 2. MySQL PK map
my_conn = pymysql.connect(**MYSQL_DSN)
my_cur = my_conn.cursor()
my_cur.execute("SHOW TABLES;")
my_tables = [r[0] for r in my_cur.fetchall()]
my_pks = {}
for t in my_tables:
    my_cur.execute(f"DESCRIBE `{t}`;")
    my_pks[t] = [c[0] for c in my_cur.fetchall() if c[3] == 'PRI']
my_conn.close()
print("MySQL PK Map loaded for", len(my_pks), "tables.")

# 3. Oracle PK map
ora_conn = oracledb.connect(**ORA_DSN)
ora_cur = ora_conn.cursor()
ora_cur.execute("""
    SELECT cols.table_name, cols.column_name
    FROM user_constraints cons
    JOIN user_cons_columns cols ON cons.constraint_name = cols.constraint_name
    WHERE cons.constraint_type = 'P' AND cols.table_name NOT LIKE 'TS_%'
    ORDER BY cols.table_name, cols.position;
""")
ora_pks = {}
for t, c in ora_cur.fetchall():
    ora_pks.setdefault(t.lower(), []).append(c.lower())
ora_conn.close()
print("Oracle PK Map loaded for", len(ora_pks), "tables.")

# 4. SQL Server PK map
ms_conn = pyodbc.connect(MSSQL_CONN_STR)
ms_cur = ms_conn.cursor()
ms_cur.execute("""
    SELECT TABLE_NAME, COLUMN_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1
    ORDER BY TABLE_NAME, ORDINAL_POSITION;
""")
ms_pks = {}
for t, c in ms_cur.fetchall():
    ms_pks.setdefault(t.lower(), []).append(c.lower())
ms_conn.close()
print("SQL Server PK Map loaded for", len(ms_pks), "tables.")

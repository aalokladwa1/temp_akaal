import pyodbc
import datetime

conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=akaal_mssql_tgt;Trusted_Connection=yes;TrustServerCertificate=yes;', autocommit=True)
cur = conn.cursor()

try:
    cur.execute('DROP TABLE mssql_batch_test')
except Exception:
    pass

cur.execute('CREATE TABLE mssql_batch_test (id INT PRIMARY KEY, val VARCHAR(100), price DECIMAL(14,4))')

data = [(i, f'Item_{i}', 99.95) for i in range(1, 5001)]
batch_size = 500

for i in range(0, len(data), batch_size):
    batch = data[i:i+batch_size]
    cur.executemany('INSERT INTO mssql_batch_test VALUES (?, ?, ?)', batch)

cur.execute('SELECT COUNT(*) FROM mssql_batch_test')
print('Batch size 500 insertion SUCCESS! Total count:', cur.fetchone()[0])
conn.close()

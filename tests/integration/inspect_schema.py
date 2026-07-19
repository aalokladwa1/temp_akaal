import oracledb

conn = oracledb.connect(user="akaal_admin", password="AkaalPass2026", host="localhost", port=1521, service_name="FREEPDB1")
cur = conn.cursor()

# Query the database dictionary metadata for the first target table's columns
cur.execute("SELECT column_name, data_type FROM user_tab_columns WHERE table_name = 'ORA_SMALL_ASSET_1' ORDER BY column_id")
print("\n--- ACTUAL ORA_SMALL_ASSET_1 COLUMNS ---")
for col in cur.fetchall():
    print(f"Column: {col[0]} | Type: {col[1]}")

cur.close()
conn.close()

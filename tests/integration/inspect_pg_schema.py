import psycopg2

conn = psycopg2.connect(host="localhost", port=5433, user="akaal_admin", password="AkaalPass2026", database="postgres")
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_schema = 'schema_small' AND table_name = 'ent_asset_4'
    ORDER BY ordinal_position;
""")

print("\n--- ACTUAL TARGET POSTGRES (ent_asset_4) COLUMNS ---")
for col in cur.fetchall():
    print(f"Column: {col[0]} | Type: {col[1]}")

cur.close()
conn.close()

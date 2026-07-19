# A:\temp_akaal\tests\integration\reseed_pg16_source.py
import psycopg2

print("[*] Re-seeding PostgreSQL 16 Source with driver-level UTF-8 enforcement...")
conn = psycopg2.connect(host="localhost", port=5432, user="akaal_admin", password="AkaalPass2026", database="postgres")
conn.set_client_encoding('UTF8') # Forces the Python driver to translate Unicode strings correctly
conn.autocommit = True
cur = conn.cursor()

for i in range(1, 21):
    table = f"schema_small.ent_asset_{i}"
    cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
    
    cur.execute(f"""
        INSERT INTO {table} (id, uuid_val, title, meta_json, payload_xml, status_emoji, created_at)
        SELECT 
            g,
            gen_random_uuid(),
            'Source Asset Title #' || g,
            jsonb_build_object('row_id', g, 'unicode_test', 'Verified Active Payload'),
            XMLPARSE(DOCUMENT '<asset><id>' || g || '</id><status>Active</status></asset>'),
            '🚀',
            NOW()
        FROM generate_series(1, 1000) g;
    """)
print("🚀 Source PostgreSQL 16 data layer successfully refreshed with true UTF-8 bytes.")
cur.close()
conn.close()
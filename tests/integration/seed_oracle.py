# A:\temp_akaal\tests\integration\seed_oracle.py
import oracledb

conn = oracledb.connect(
    user="akaal_admin",
    password="AkaalPass2026",
    host="localhost",
    port=1521,
    service_name="FREEPDB1"
)
cur = conn.cursor()

cur.execute("SELECT table_name FROM user_tables WHERE table_name LIKE 'ORA_SMALL_%'")
tables = [r[0] for r in cur.fetchall()]

print(f"[*] Re-seeding {len(tables)} tables with strict UUID specifications...")

for table in tables:
    # Clear out the malformed text entries first
    cur.execute(f'TRUNCATE TABLE "{table}"')
    
    # LOWER(RAWTOHEX(SYS_GUID())) creates a compliant 32-character pure hex string 
    # that PostgreSQL natively translates directly into its standard UUID type.
    cur.execute(f"""
        INSERT INTO "{table}" (ID, UUID_VAL, TITLE, META_JSON, PAYLOAD_CLOB, PAYLOAD_BLOB, CREATED_AT)
        SELECT 
            LEVEL,
            LOWER(RAWTOHEX(SYS_GUID())),
            'Asset Title Entry #' || LEVEL,
            '{{"engine": "oracle_23ai", "metric_id": ' || LEVEL || ', "status": "verified"}}',
            'Sample massive text payload for asset validation level number ' || LEVEL,
            utl_raw.cast_to_raw('Binary asset buffer sequence stream ' || LEVEL),
            SYSTIMESTAMP
        FROM DUAL
        CONNECT BY LEVEL <= 100
    """)
    print(f"  ✅ Regenerated valid payloads for: {table}")

conn.commit()
cur.close()
conn.close()
print("================")
print("🚀 Compliant Oracle data layer refresh complete.")
import oracledb

# Extended candidate pool including container roots, unicode defaults, and common variations
candidates = [
    'FREEPDB1', 'FREE', 'XE', 'ORCL', 'ORCLPDB1', 'XEPDB1', 'akaal', 'akaal_src',
    'CDB$ROOT', 'PDBORCL', 'ORCLPDB', 'XEINTERNAL', 'SYS$BACKGROUND'
]
print("\n=== SYSTEM CONNECTIONS DISCOVERY MATRIX V2 ===")

for target in candidates:
    # Test as a Service Name
    try:
        conn = oracledb.connect(user="akaal_admin", password="AkaalPass2026", host="localhost", port=1521, service_name=target)
        print(f"  ? SUCCESS: Found Active SERVICE_NAME -> {target}")
        conn.close()
        import sys; sys.exit(0)
    except Exception as e:
        pass

    # Test as a legacy SID
    try:
        conn = oracledb.connect(user="akaal_admin", password="AkaalPass2026", host="localhost", port=1521, sid=target)
        print(f"  ? SUCCESS: Found Active SID -> {target}")
        conn.close()
        import sys; sys.exit(0)
    except Exception as e:
        pass
else:
    # If all fail, let's catch the exact raw error string of the primary default to see if it lists alternatives
    try:
        oracledb.connect(user="akaal_admin", password="AkaalPass2026", host="localhost", port=1521, service_name="FREEPDB1")
    except Exception as final_err:
        print(f"\n? Diagnostic Raw Response Error:\n{final_err}")

import oracledb

candidates = ['FREEPDB1', 'FREE', 'XE', 'ORCL', 'ORCLPDB1', 'XEPDB1', 'akaal', 'akaal_src']
print("\n=== SYSTEM CONNECTIONS DISCOVERY ACTIVE ===")

for target in candidates:
    # Test as a Service Name
    try:
        conn = oracledb.connect(user="akaal_admin", password="AkaalPass2026", host="localhost", port=1521, service_name=target)
        print(f"  ? SUCCESS: Found Active SERVICE_NAME -> {target}")
        conn.close()
        break
    except Exception:
        pass

    # Test as a legacy SID
    try:
        conn = oracledb.connect(user="akaal_admin", password="AkaalPass2026", host="localhost", port=1521, sid=target)
        print(f"  ? SUCCESS: Found Active SID -> {target}")
        conn.close()
        break
    except Exception:
        pass
else:
    print("? ERROR: All standard Oracle descriptors failed to resolve.")

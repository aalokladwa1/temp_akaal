import oracledb

# Expanded target matrix covering common training, production, and custom pluggable environments
candidates = [
    'pdb1', 'orclpdb', 'orclpdb1', 'prod', 'dev', 'test', 'db23ai', 'sample', 
    'freepdb1', 'free', 'xe', 'orcl', 'akaal', 'akaaldedicated'
]

print("\n=== SYSTEM CONNECTIONS DISCOVERY MATRIX V3 ===")
found = False

for target in candidates:
    # 1. Try case variations as a Service Name
    for name in [target, target.lower(), target.upper()]:
        try:
            conn = oracledb.connect(user="akaal_admin", password="AkaalPass2026", host="localhost", port=1521, service_name=name)
            print(f"  ? SUCCESS: Found Active SERVICE_NAME -> {name}")
            conn.close()
            found = True
            break
        except Exception:
            pass
            
        try:
            conn = oracledb.connect(user="akaal_admin", password="AkaalPass2026", host="localhost", port=1521, sid=name)
            print(f"  ? SUCCESS: Found Active SID -> {name}")
            conn.close()
            found = True
            break
        except Exception:
            pass
    if found:
        break
else:
    print("? ERROR: All custom institutional service names failed to resolve.")

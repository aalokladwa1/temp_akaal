"""
AKAAL Day 21 — Multi-Engine Verification & Live Acceptance Test Script
========================================================================
Validates PostgreSQL -> Oracle discovery, cache identity, engine-aware contracts,
and Oracle regression testing.
"""

import sys
import json
import psycopg2
from akaal.gateway.engine_gateway import EngineGateway

def test_direct_postgres_catalog():
    print("--- 1. Direct PostgreSQL Catalog Query ---")
    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        dbname="pg_analytics",
        user="postgres",
        password="postgres"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema IN ('sch_alpha', 'sch_beta')
          AND table_type = 'BASE TABLE'
        ORDER BY table_schema, table_name
    """)
    rows = cur.fetchall()
    conn.close()
    print(f"Direct PG catalog objects: {rows}")
    expected = [('sch_alpha', 'tbl_users'), ('sch_beta', 'tbl_metrics')]
    assert rows == expected, f"Direct catalog mismatch: got {rows}, expected {expected}"
    print("[SUCCESS] Direct PostgreSQL catalog query verified!\n")

def test_engine_gateway_postgres():
    print("--- 2. EngineGateway PostgreSQL Preflight & Discovery ---")
    gateway = EngineGateway()
    
    # Connection test
    conn_res = gateway.test_connection({
        "system_type": "POSTGRESQL",
        "host": "localhost",
        "port": 5433,
        "database_name": "pg_analytics",
        "username": "postgres",
        "password": "postgres"
    })
    print("PostgreSQL Connection Test:", json.dumps(conn_res, indent=2))
    assert conn_res.get("connected") is True, f"PG Connection test failed: {conn_res}"

    # Preflight discovery
    preflight_res = gateway.run_preflight({
        "source_engine": "PostgreSQL 16",
        "source_host": "localhost",
        "source_port": 5433,
        "source_db": "pg_analytics",
        "source_user": "postgres",
        "source_pass": "postgres",
        "target_engine": "Oracle 19c"
    })
    print("PostgreSQL Discovery Report Summary:")
    print("Snapshot ID:", preflight_res.get("discovery_snapshot_id"))
    print("Metrics:", preflight_res.get("metrics"))
    
    databases = preflight_res.get("instance", {}).get("databases", [])
    assert len(databases) > 0, "No databases returned in discovery!"
    
    pg_db = databases[0]
    assert pg_db.get("database_name") == "pg_analytics" or pg_db.get("db_name") == "pg_analytics" or pg_db.get("db_id") == "db-PG_ANALYTICS"
    
    schema_map = {str(s.get("schema_name", "")).upper(): s for s in pg_db.get("schemas", []) if s.get("schema_name")}
    print("Discovered Schemas in PG:", list(schema_map.keys()))
    assert "SCH_ALPHA" in schema_map, f"SCH_ALPHA schema missing from {list(schema_map.keys())}"
    assert "SCH_BETA" in schema_map, f"SCH_BETA schema missing from {list(schema_map.keys())}"
    
    # Check SCH_ALPHA objects
    alpha_objs = [
        obj["object_name"].upper()
        for grp in schema_map["SCH_ALPHA"].get("object_groups", [])
        for obj in grp.get("objects", [])
    ]
    assert "TBL_USERS" in alpha_objs, f"TBL_USERS missing from SCH_ALPHA: {alpha_objs}"

    # Check SCH_BETA objects
    beta_objs = [
        obj["object_name"].upper()
        for grp in schema_map["SCH_BETA"].get("object_groups", [])
        for obj in grp.get("objects", [])
    ]
    assert "TBL_METRICS" in beta_objs, f"TBL_METRICS missing from SCH_BETA: {beta_objs}"
    
    print("[SUCCESS] EngineGateway PostgreSQL discovery verified!\n")
    return preflight_res

def test_engine_gateway_oracle_regression():
    print("--- 3. Oracle Discovery Regression Test ---")
    gateway = EngineGateway()
    
    conn_res = gateway.test_connection({
        "system_type": "ORACLE",
        "host": "localhost",
        "port": 1521,
        "database_name": "instance2_pdb",
        "username": "o",
        "password": "password"
    })
    print("Oracle Connection Test:", json.dumps(conn_res, indent=2))
    assert conn_res.get("connected") is True, f"Oracle Connection test failed: {conn_res}"

    preflight_res = gateway.run_preflight({
        "source_engine": "Oracle 19c",
        "source_host": "localhost",
        "source_port": 1521,
        "source_db": "instance2_pdb",
        "source_user": "o",
        "source_pass": "password",
        "target_engine": "PostgreSQL 16"
    })
    print("Oracle Discovery Report Summary:")
    print("Snapshot ID:", preflight_res.get("discovery_snapshot_id"))
    print("Metrics:", preflight_res.get("metrics"))

    databases = preflight_res.get("instance", {}).get("databases", [])
    assert len(databases) > 0, "No Oracle databases returned in discovery!"
    
    ora_db = databases[0]
    assert ora_db.get("database_name") == "INSTANCE2_PDB" or ora_db.get("db_name") == "INSTANCE2_PDB"
    
    schema_names = [s["schema_name"].upper() for s in ora_db.get("schemas", [])]
    print("Discovered Schemas in Oracle:", schema_names)
    expected_schemas = ["USR_ANALYTICS", "USR_FINANCE", "USR_OPS"]
    for s_name in expected_schemas:
        assert s_name in schema_names, f"Oracle schema {s_name} missing from {schema_names}"

    print("[SUCCESS] Oracle Discovery Regression Verified!\n")

if __name__ == "__main__":
    try:
        test_direct_postgres_catalog()
        test_engine_gateway_postgres()
        test_engine_gateway_oracle_regression()
        print("=========================================================")
        print("ALL DAY 21 MULTI-ENGINE DISCOVERY VERIFICATIONS PASSED 100%")
        print("=========================================================")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FAILURE] Verification failed: {e}")
        sys.exit(1)

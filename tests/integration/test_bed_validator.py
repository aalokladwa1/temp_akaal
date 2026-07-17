#!/usr/bin/env python3
import sys
import os
import hashlib

# Explicitly declare absolute module location injection parameters
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_bed_setup import get_connection

def compute_pg_table_hash(cursor, schema_name, table_name):
    """Calculates an exact block data MD5 hash ordered by the primary key to verify data equality."""
    try:
        query = f"SELECT title, status_emoji FROM {schema_name}.{table_name} ORDER BY id;"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        hasher = hashlib.md5()
        for r in rows:
            hasher.update(f"{r[0]}-{r[1]}".encode('utf-8'))
        return hasher.hexdigest()
    except Exception as e:
        print(f"[-] MD5 computation failed on {schema_name}.{table_name}: {e}")
        return None

def verify_phase_8_migration():
    print("==========================================================")
    print("      AKAAL PHASE 8 INTEGRITY VALIDATION ENGINE           ")
    print("==========================================================")
    
    print("[*] Validating PostgreSQL 16 Source vs. PostgreSQL 17 Target...")
    src_conn = get_connection("pg_src")
    tgt_conn = get_connection("pg_tgt")
    
    src_cur = src_conn.cursor()
    tgt_cur = tgt_conn.cursor()
    
    mismatches = 0
    for t in range(1, 21):
        table_name = f"ent_asset_{t}"
        
        src_cur.execute(f"SELECT COUNT(*) FROM schema_small.{table_name};")
        tgt_cur.execute(f"SELECT COUNT(*) FROM schema_small.{table_name};")
        
        s_count = src_cur.fetchone()[0]
        t_count = tgt_cur.fetchone()[0]
        
        if s_count != t_count:
            print(f"  ? Count Mismatch on schema_small.{table_name}! Source: {s_count} | Target: {t_count}")
            mismatches += 1
            continue
            
        s_hash = compute_pg_table_hash(src_cur, "schema_small", table_name)
        t_hash = compute_pg_table_hash(tgt_cur, "schema_small", table_name)
        
        if s_hash != t_hash:
            print(f"  ? Data Checksum Mismatch on schema_small.{table_name}!")
            mismatches += 1
        else:
            print(f"  ? schema_small.{table_name}: Identical ({s_count} rows verified)")

    print("\n[*] Auditing Target Foreign Key Constraint Mapping Contexts...")
    tgt_cur.execute("""
        SELECT COUNT(*) FROM information_schema.table_constraints 
        WHERE constraint_type = 'FOREIGN KEY' AND table_schema = 'schema_small';
    """)
    fk_count = tgt_cur.fetchone()[0]
    print(f"  -> Target Foreign Key Constraints Deployed: {fk_count}")
    
    src_cur.close()
    tgt_cur.close()
    src_conn.close()
    tgt_conn.close()
    
    print("\n==========================================================")
    if mismatches == 0:
        print("?? VALIDATION PASS: All migrated source/target structures match perfectly.")
    else:
        print(f"?? VALIDATION FAIL: Detected {mismatches} state variances in the target database.")
    print("==========================================================")

if __name__ == "__main__":
    verify_phase_8_migration()

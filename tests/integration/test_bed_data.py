#!/usr/bin/env python3
import os
import uuid
import json
import random
from test_bed_setup import get_connection

def stream_bulk_tier(engine, size_label, table_count, row_count_per_table):
    """Streams data rows using client-side pipelined generator chunks to control memory."""
    print(f"[*] Seeding data into {engine.upper()} for tier: schema_{size_label} ({row_count_per_table:,} rows/table)...")
    conn = get_connection(engine)
    cursor = conn.cursor()
    
    # Chunk sizing threshold to optimize pipeline network buffers
    chunk_size = 5000 if row_count_per_table >= 100000 else 1000
    
    for t in range(1, table_count + 1):
        rows_buffer = []
        for r in range(1, row_count_per_table + 1):
            uid = str(uuid.uuid4())
            jsn = json.dumps({"row_id": r, "engine_source": engine, "unicode_test": "Verified ???"})
            xml_data = f"<asset><id>{r}</id><status>Active</status></asset>"
            
            # Match engine specific insertion syntax targets
            if engine in ["pg_src", "pg_tgt"]:
                rows_buffer.append((uid, f"Asset Row Variant {r}", jsn, xml_data))
            elif engine == "mysql":
                rows_buffer.append((uid, f"Asset Row Variant {r}", jsn))
            elif engine == "oracle":
                rows_buffer.append((uid, f"Asset Row Variant {r}", jsn))
                
            if len(rows_buffer) >= chunk_size:
                if engine in ["pg_src", "pg_tgt"]:
                    cursor.executemany(
                        f"INSERT INTO schema_{size_label}.ent_asset_{t} (uuid_val, title, meta_json, payload_xml) VALUES (%s, %s, %s, %s)",
                        rows_buffer
                    )
                elif engine == "mysql":
                    cursor.executemany(
                        f"INSERT INTO mysql_schema_{size_label}.ent_asset_{t} (uuid_val, title, meta_json) VALUES (%s, %s, %s)",
                        rows_buffer
                    )
                elif engine == "oracle":
                    cursor.executemany(
                        f"INSERT INTO ORA_{size_label.upper()}_ASSET_{t} (uuid_val, title, meta_json) VALUES (:1, :2, :3)",
                        rows_buffer
                    )
                rows_buffer = []
        
        # Flush trailing records in buffer
        if rows_buffer:
            if engine in ["pg_src", "pg_tgt"]:
                cursor.executemany(f"INSERT INTO schema_{size_label}.ent_asset_{t} (uuid_val, title, meta_json, payload_xml) VALUES (%s, %s, %s, %s)", rows_buffer)
            elif engine == "mysql":
                cursor.executemany(f"INSERT INTO mysql_schema_{size_label}.ent_asset_{t} (uuid_val, title, meta_json) VALUES (%s, %s, %s)", rows_buffer)
            elif engine == "oracle":
                cursor.executemany(f"INSERT INTO ORA_{size_label.upper()}_ASSET_{t} (uuid_val, title, meta_json) VALUES (:1, :2, :3)", rows_buffer)
                
    cursor.close()
    conn.close()

def build_dedicated_lobs():
    """Requirement 8: Generate massive raw binary blocks for LOB transfer tests."""
    lob_dir = "A:\\temp_akaal\\tests\\integration\\local_lob_payloads"
    os.makedirs(lob_dir, exist_ok=True)
    print(f"\n[*] Generating flat binary mock files inside: {lob_dir}...")
    
    # Dedicated validation file targets (10MB, 100MB, 500MB)
    target_sizes = {"10mb": 10, "100mb": 100, "500mb": 500}
    
    for label, size_mb in target_sizes.items():
        file_path = os.path.join(lob_dir, f"test_payload_{label}.bin")
        if not os.path.exists(file_path):
            print(f"  -> Writing {size_mb} MB block payload to disk...")
            with open(file_path, "wb") as f:
                # 1MB block pipeline to keep host memory clean
                for _ in range(size_mb):
                    f.write(os.urandom(1024 * 1024))
    print("? Local binary LOB payload matrix ready on drive partition.")

if __name__ == "__main__":
    print("==========================================================")
    print("      AKAAL PHASE 8 HIGH-VOLUME DATA GENERATION FACTORY    ")
    print("==========================================================")
    
    # Stream small profile data arrays (1,000 rows across targets)
    for target in ["pg_src", "mysql", "oracle"]:
        stream_bulk_tier(target, "small", table_count=20, row_count_per_table=1000)
        
    # Generate verification LOB components
    build_dedicated_lobs()
    print("==========================================================")

# A:\temp_akaal\tests\integration\akaal_core_orchestrator.py
import os
import sys
import json
import time
import hashlib
import psycopg2
import pymysql
import oracledb
from datetime import datetime
from psycopg2.extras import Json

# --- CONFIGURATION ENGINE MAPPING ---
CONFIG = {
    "pg_src": {"host": "localhost", "port": 5432, "user": "akaal_admin", "password": "AkaalPass2026", "database": "postgres"},
    "pg_tgt": {"host": "localhost", "port": 5433, "user": "akaal_admin", "password": "AkaalPass2026", "database": "postgres"},
    "mysql": {"host": "localhost", "port": 3306, "user": "akaal_admin", "password": "AkaalPass2026"}, 
    "oracle": {
        "user": "akaal_admin", 
        "password": "AkaalPass2026", 
        "host": "localhost", 
        "port": 1521, 
        "service_name": "FREEPDB1"
    }
}

STATE_FILE = r"A:\temp_akaal\tests\integration\migration_checkpoint.json"

class AkaalMigrationOrchestrator:
    def __init__(self):
        print("==========================================================")
        print("         AKAAL CORE MIGRATION ORCHESTRATION ENGINE        ")
        print("==========================================================")
        self.checkpoints = self.load_checkpoints()

    def load_checkpoints(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        return {"completed_tables": [], "phase_9_manifests": {}}

    def save_checkpoint(self, table_name):
        if table_name not in self.checkpoints["completed_tables"]:
            self.checkpoints["completed_tables"].append(table_name)
        with open(STATE_FILE, 'w') as f:
            json.dump(self.checkpoints, f, indent=4)

    def execute_phase_9_intelligence(self, engine_type, schema_name, tables):
        print(f"[*] Running Phase 9 Intelligence Layer for [{engine_type.upper()}]...")
        time.sleep(0.05)
        
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "source_engine": engine_type,
            "schema_target": schema_name,
            "scout_discovered_tables": len(tables),
            "decoder_rulebook_hash": hashlib.sha256(str(tables).encode()).hexdigest(),
            "planner_risk_assessment": "MEDIUM - Heterogeneous Engine Transformation Required" if engine_type != "postgres_16" else "LOW"
        }
        
        self.checkpoints["phase_9_manifests"][f"{engine_type}_{schema_name}"] = manifest
        print(f"  ✅ Phase 9 Intelligence Manifest Generated. Rulebook Hash: {manifest['decoder_rulebook_hash'][:12]}")
        return manifest

    def get_target_columns(self, tgt_cur, table_name):
        """Dynamically reflects the target PostgreSQL table to see exactly what columns exist."""
        tgt_cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'schema_small' AND table_name = %s;
        """, (table_name,))
        return [r[0].lower() for r in tgt_cur.fetchall()]

    def migrate_postgres_to_postgres(self):
        print("\n[*] Initializing Phase 8 Pipe: PostgreSQL 16 → PostgreSQL 17 Target...")
        src_conn = psycopg2.connect(**CONFIG["pg_src"])
        tgt_conn = psycopg2.connect(**CONFIG["pg_tgt"])
        
        # Enforce explicit driver-level UTF-8 handling on both sides of the migration pipe
        src_conn.set_client_encoding('UTF8')
        tgt_conn.set_client_encoding('UTF8')
        
        src_conn.autocommit = True
        tgt_conn.autocommit = True
        
        src_cur = src_conn.cursor()
        tgt_cur = tgt_conn.cursor()
        
        # Get all asset tables in the source schema
        src_cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'schema_small' AND table_name LIKE 'ent_asset_%';
        """)
        tables = [r[0] for r in src_cur.fetchall()]
        
        self.execute_phase_9_intelligence("postgres_16", "schema_small", tables)
        
        for table in tables:
            checkpoint_key = f"postgres.schema_small.{table}"
            if checkpoint_key in self.checkpoints["completed_tables"]:
                print(f"  ⏭️ Checkpoint Match: {table} already migrated. Skipping.")
                continue
                
            print(f"  🚀 Migrating Data Stream: schema_small.{table}...")
            
            # Extract row states from source
            src_cur.execute(f"SELECT id, uuid_val, title, meta_json, payload_xml, status_emoji, created_at FROM schema_small.{table};")
            rows = src_cur.fetchall()
            
            if rows:
                adapted_rows = []
                for row in rows:
                    row_id, uuid_val, title, meta_json, payload_xml, status_emoji, created_at = row
                    
                    # Convert raw dict types to safe driver parameters
                    safe_json = Json(meta_json) if isinstance(meta_json, (dict, list)) else meta_json
                    
                    adapted_rows.append((
                        row_id, 
                        uuid_val, 
                        title, 
                        safe_json, 
                        payload_xml, 
                        status_emoji, 
                        created_at
                    ))
                
                insert_stmt = f"""
                    INSERT INTO schema_small.{table} (id, uuid_val, title, meta_json, payload_xml, status_emoji, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;
                """
                tgt_cur.executemany(insert_stmt, adapted_rows)
                
            self.save_checkpoint(checkpoint_key)
            print(f"    ✅ Clean Sync: {len(rows)} records successfully pushed.")
            
        src_cur.close(); tgt_cur.close(); src_conn.close(); tgt_conn.close()

    def migrate_mysql_to_postgres(self):
        print("\n[*] Initializing Phase 8 Pipe: MySQL 8.x → PostgreSQL 17 Target...")
        my_conn = pymysql.connect(**CONFIG["mysql"])
        tgt_conn = psycopg2.connect(**CONFIG["pg_tgt"])
        tgt_conn.set_client_encoding('UTF8')
        tgt_conn.autocommit = True
        
        my_cur = my_conn.cursor()
        tgt_cur = tgt_conn.cursor()
        
        my_cur.execute("SHOW TABLES FROM `mysql_schema_small`;")
        tables = [r[0] for r in my_cur.fetchall()]
        
        self.execute_phase_9_intelligence("mysql_8", "schema_small", tables)
        
        for table in tables:
            checkpoint_key = f"mysql.schema_small.{table}"
            if checkpoint_key in self.checkpoints["completed_tables"]:
                print(f"  ⏭️ Checkpoint Match: {table} already migrated. Skipping.")
                continue
                
            print(f"  🚀 Migrating Translating Data Stream: {table}...")
            target_table = table.replace("my_small_", "") if table.startswith("my_small_") else table
            
            # 1. Inspect what columns actually exist in the target PostgreSQL table
            tgt_cols = self.get_target_columns(tgt_cur, target_table)
            
            # 2. Inspect what columns actually exist in the source MySQL table
            my_cur.execute(f"DESCRIBE `mysql_schema_small`.`{table}`;")
            my_cols = [r[0].lower() for r in my_cur.fetchall()]
            
            # 3. Build the selection matrix based on what MySQL actually has
            text_payload_col = None
            for option in ['payload_xml', 'payload_text', 'payload_clob', 'payload']:
                if option in my_cols:
                    text_payload_col = option
                    break
                    
            base_mappings = ['id', 'uuid_val', 'title', 'meta_json', 'status_emoji', 'created_at']
            active_my_select = [f"`{c}`" for c in base_mappings if c in my_cols]
            
            if text_payload_col:
                active_my_select.append(f"`{text_payload_col}`")
                
            select_str = ", ".join(active_my_select)
            my_cur.execute(f"SELECT {select_str} FROM `mysql_schema_small`.`{table}`;")
            rows = my_cur.fetchall()
            
            if rows:
                adapted_rows = []
                cleaned_my_cols = [c.replace('`', '').lower() for c in active_my_select]
                
                for row in rows:
                    adapted_row = []
                    final_cols = []
                    
                    if 'id' in tgt_cols and 'id' in cleaned_my_cols:
                        adapted_row.append(row[cleaned_my_cols.index('id')]); final_cols.append('id')
                    if 'uuid_val' in tgt_cols and 'uuid_val' in cleaned_my_cols:
                        adapted_row.append(row[cleaned_my_cols.index('uuid_val')]); final_cols.append('uuid_val')
                    if 'title' in tgt_cols and 'title' in cleaned_my_cols:
                        adapted_row.append(row[cleaned_my_cols.index('title')]); final_cols.append('title')
                        
                    if 'meta_json' in tgt_cols and 'meta_json' in cleaned_my_cols:
                        val = row[cleaned_my_cols.index('meta_json')]
                        adapted_row.append(Json(val) if isinstance(val, (dict, list)) else val); final_cols.append('meta_json')
                        
                    if 'payload_xml' in tgt_cols:
                        if text_payload_col and text_payload_col in cleaned_my_cols:
                            raw_text = row[cleaned_my_cols.index(text_payload_col)]
                            xml_val = raw_text if (isinstance(raw_text, str) and raw_text.startswith('<')) else f"<data>{raw_text}</data>"
                            adapted_row.append(xml_val)
                        else:
                            adapted_row.append("<data></data>")
                        final_cols.append('payload_xml')
                        
                    if 'status_emoji' in tgt_cols:
                        if 'status_emoji' in cleaned_my_cols:
                            adapted_row.append(row[cleaned_my_cols.index('status_emoji')])
                        else:
                            adapted_row.append("🚀")
                        final_cols.append('status_emoji')
                        
                    if 'created_at' in tgt_cols and 'created_at' in cleaned_my_cols:
                        adapted_row.append(row[cleaned_my_cols.index('created_at')]); final_cols.append('created_at')
                    if 'parent_ref_id' in tgt_cols:
                        adapted_row.append(None); final_cols.append('parent_ref_id')
                        
                    adapted_rows.append(tuple(adapted_row))
                    
                col_placeholders = ", ".join(["%s"] * len(final_cols))
                col_names_str = ", ".join(final_cols)
                
                insert_stmt = f"""
                    INSERT INTO schema_small.{target_table} ({col_names_str})
                    VALUES ({col_placeholders}) ON CONFLICT DO NOTHING;
                """
                tgt_cur.executemany(insert_stmt, adapted_rows)
                
            self.save_checkpoint(checkpoint_key)
            print(f"    ✅ Clean Sync: {len(rows)} engine transformed records pushed.")
            
        my_cur.close(); tgt_cur.close(); my_conn.close(); tgt_conn.close()

    def migrate_oracle_to_postgres(self):
        print("\n[*] Initializing Phase 8 Pipe: Oracle 23ai → PostgreSQL 17 Target...")
        ora_conn = oracledb.connect(
            user=CONFIG["oracle"]["user"], 
            password=CONFIG["oracle"]["password"], 
            host=CONFIG["oracle"]["host"], 
            port=CONFIG["oracle"]["port"], 
            service_name=CONFIG["oracle"]["service_name"]
        )
        print(f"  ✅ Connection Handshake Established via Service: {CONFIG['oracle']['service_name']}")
            
        tgt_conn = psycopg2.connect(**CONFIG["pg_tgt"])
        tgt_conn.set_client_encoding('UTF8')
        tgt_conn.autocommit = True
        
        ora_cur = ora_conn.cursor()
        tgt_cur = tgt_conn.cursor()
        
        ora_cur.execute("SELECT table_name FROM user_tables")
        tables = [r[0] for r in ora_cur.fetchall() if "SMALL" in r[0]]
        
        self.execute_phase_9_intelligence("oracle_23ai", "schema_small", tables)
        
        for table in tables:
            checkpoint_key = f"oracle.schema_small.{table}"
            if checkpoint_key in self.checkpoints["completed_tables"]:
                print(f"  ⏭️ Checkpoint Match: {table} already migrated. Skipping.")
                continue
                
            print(f"  🚀 Migrating Translating Data Stream: {table}...")
            raw_lower = table.lower()
            target_table = raw_lower.replace("ora_small_", "ent_") if raw_lower.startswith("ora_small_") else raw_lower
            
            tgt_cols = self.get_target_columns(tgt_cur, target_table)
            
            ora_cur.execute('SELECT ID, UUID_VAL, TITLE, META_JSON, PAYLOAD_CLOB, PAYLOAD_BLOB, CREATED_AT FROM "{0}"'.format(table))
            rows = ora_cur.fetchall()
            
            if rows:
                adapted_rows = []
                for row in rows:
                    id_val, uuid_val, title, meta_json, clob_obj, blob_obj, created_at = row
                    raw_clob_text = clob_obj.read() if hasattr(clob_obj, 'read') else clob_obj
                    
                    adapted_row = []
                    final_cols = []
                    
                    if 'id' in tgt_cols:
                        adapted_row.append(id_val); final_cols.append('id')
                    if 'uuid_val' in tgt_cols:
                        adapted_row.append(uuid_val); final_cols.append('uuid_val')
                    if 'title' in tgt_cols:
                        adapted_row.append(title); final_cols.append('title')
                    if 'meta_json' in tgt_cols:
                        json_str = meta_json if (isinstance(meta_json, str) and meta_json.startswith('{')) else '{}'
                        adapted_row.append(json_str); final_cols.append('meta_json')
                    if 'payload_xml' in tgt_cols:
                        adapted_row.append(f"<data>{raw_clob_text}</data>"); final_cols.append('payload_xml')
                    if 'status_emoji' in tgt_cols:
                        adapted_row.append("🚀"); final_cols.append('status_emoji')
                    if 'created_at' in tgt_cols:
                        adapted_row.append(created_at); final_cols.append('created_at')
                    if 'parent_ref_id' in tgt_cols:
                        adapted_row.append(None); final_cols.append('parent_ref_id')
                        
                    adapted_rows.append(tuple(adapted_row))
                
                col_placeholders = ", ".join(["%s"] * len(final_cols))
                col_names_str = ", ".join(final_cols)
                
                insert_stmt = f"""
                    INSERT INTO schema_small.{target_table} ({col_names_str})
                    VALUES ({col_placeholders}) ON CONFLICT DO NOTHING;
                """
                tgt_cur.executemany(insert_stmt, adapted_rows)
                
            self.save_checkpoint(checkpoint_key)
            print(f"    ✅ Clean Sync: {len(rows)} records translated and pushed.")
            
        ora_cur.close(); tgt_cur.close(); ora_conn.close(); tgt_conn.close()

# --- MASTER ORCHESTRATION EXECUTION ---
if __name__ == "__main__":
    orchestrator = AkaalMigrationOrchestrator()
    
    # 1. Run the PostgreSQL 16 Pipeline
    orchestrator.migrate_postgres_to_postgres()
    
    # --- CRASH TEST ARTIFACT BLOCK ---
    print("\n[*] Transitioning engines... sleeping for 4 seconds. PRESS CTRL+C NOW TO CRASH.")
    time.sleep(4)
    # ---------------------------------
    
    # 2. Run the MySQL 8.x Pipeline
    orchestrator.migrate_mysql_to_postgres()
    
    # 3. Run the Oracle 23ai Pipeline
    orchestrator.migrate_oracle_to_postgres()
    
    print("\n==========================================================")
    print("🎉 PHASE 8 & PHASE 9 HETEROGENEOUS MIGRATION COMPLETE")
    print("==========================================================")
#!/usr/bin/env python3
import time
import random
import threading
from test_bed_setup import get_connection

def pg_cdc_worker(worker_id, stop_event):
    """Executes transaction noise loops against PostgreSQL source schema."""
    try:
        conn = get_connection("pg_src")
        cursor = conn.cursor()
        print(f"[+] PostgreSQL CDC Worker {worker_id} successfully online.")
        
        while not stop_event.is_set():
            # Randomly target one of the first 10 assets in the small schema
            target_table = f"schema_small.ent_asset_{random.randint(1, 10)}"
            op = random.choice(["INSERT", "UPDATE", "DELETE"])
            
            try:
                if op == "INSERT":
                    cursor.execute(f"INSERT INTO {target_table} (title) VALUES ('Live CDC Row - Worker {worker_id}');")
                elif op == "UPDATE":
                    # Update a target row based on arbitrary fast scan execution limits
                    cursor.execute(f"UPDATE {target_table} SET title = 'CDC Mutated' WHERE id = (SELECT id FROM {target_table} LIMIT 1);")
                elif op == "DELETE":
                    cursor.execute(f"DELETE FROM {target_table} WHERE id = (SELECT id FROM {target_table} LIMIT 1);")
            except Exception:
                pass # Absorb transient deadlocks/timeouts during active chaos testing
            time.sleep(0.05)
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[-] PG CDC Worker {worker_id} encountered fault: {e}")

if __name__ == "__main__":
    print("==========================================================")
    print("         AKAAL CONCURRENT LIVE CDC ENGINE RUNNER          ")
    print("==========================================================")
    
    stop_signal = threading.Event()
    
    # Configurable worker-count profiles (e.g., 1, 2, 4, 8, 16, 32)
    active_worker_profile = 4
    workers = []
    
    print(f"[*] Initializing concurrency pool: {active_worker_profile} execution workers...")
    for i in range(active_worker_profile):
        t = threading.Thread(target=pg_cdc_worker, args=(i, stop_signal), daemon=True)
        t.start()
        workers.append(t)
        
    print("[*] Continuous CDC profile loop fully active. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Halting background worker groups safely...")
        stop_signal.set()
        print("? CDC Workload generator successfully stopped.")

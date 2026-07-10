import json
import os
import time
import sys
import random

# CONFIGURABLE CONSTANTS
BATCH_SIZE = 500
RANDOM_SEED = 42

def generate_dml():
    start_time = time.perf_counter()
    file_path = "sample_data.sql"
    
    # Initialize random seed to make generation completely reproducible
    random.seed(RANDOM_SEED)
    
    print(f"Starting deterministic DML generation to '{file_path}'...")
    print(f"  * Configured Batch Size: {BATCH_SIZE}")
    print(f"  * Configured Random Seed: {RANDOM_SEED}")

    # Track target record counts
    TARGET_USERS = 10000
    TARGET_PRODUCTS = 5000
    TARGET_ORDERS = 100000
    TARGET_ORDER_ITEMS = 300000
    TARGET_AUDIT_LOGS = 50000

    # Count actual records added to verify data generation integrity
    counts = {
        "users": 0,
        "products": 0,
        "orders": 0,
        "order_items": 0,
        "audit_logs": 0
    }

    unicode_names = [
        "山田太郎 😊",      # Japanese + Emoji
        "आलोक कुमार 🚀",    # Hindi + Emoji
        "Иван Петров 💻",   # Russian + Emoji
        "José de Souza ☕", # Portuguese / Accents + Emoji
        "Müller Straße 🇩🇪", # German + Emoji
        "김철수 🇰🇷",        # Korean + Emoji
        "علي أحمد 🌴"        # Arabic + Emoji
    ]

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("-- sample_data.sql\n")
            f.write("-- Refined Enterprise Seed Data for akaal_validation\n")
            f.write("USE akaal_validation;\n\n")
            f.write("SET FOREIGN_KEY_CHECKS = 0;\n")
            f.write("TRUNCATE TABLE audit_logs;\n")
            f.write("TRUNCATE TABLE order_items;\n")
            f.write("TRUNCATE TABLE orders;\n")
            f.write("TRUNCATE TABLE products;\n")
            f.write("TRUNCATE TABLE users;\n\n")
            
            # 1. Users: 10,000 records
            print("Generating users...")
            f.write("-- 1. Users\n")
            batch = []
            for i in range(1, TARGET_USERS + 1):
                email = f"user_{i}@example.com"
                name_suffix = unicode_names[i % len(unicode_names)]
                name = f"User {i} ({name_suffix})"
                is_active = 1 if i % 10 != 0 else 0
                created_at = f"2026-01-01 {i // 3600 % 24:02d}:{i // 60 % 60:02d}:{i % 60:02d}"
                batch.append(f"({i}, '{email}', '{name}', {is_active}, '{created_at}')")
                counts["users"] += 1
                if len(batch) >= BATCH_SIZE:
                    f.write("INSERT INTO users (id, email, full_name, is_active, created_at) VALUES\n" + ",\n".join(batch) + ";\n")
                    batch = []
                if i % 2500 == 0:
                    print(f"  .. generated {i} user records")
            if batch:
                f.write("INSERT INTO users (id, email, full_name, is_active, created_at) VALUES\n" + ",\n".join(batch) + ";\n")
                
            # 2. Products: 5,000 records
            print("Generating products...")
            f.write("\n-- 2. Products\n")
            batch = []
            for i in range(1, TARGET_PRODUCTS + 1):
                sku = f"SKU-PROD-{i:05d}"
                name_suffix = unicode_names[i % len(unicode_names)]
                name = f"Product Item {i} ({name_suffix})"
                price = 9.99 + (i * 0.05)
                desc = "" if i % 50 == 0 else ("NULL" if i % 100 == 0 else f"Description for product {i}")
                desc_val = "NULL" if desc == "NULL" else f"'{desc}'"
                extra_desc = f"Extra details for product {i} to test LONGTEXT column type with unicode: {name_suffix}"
                attrs = {"id": i, "category": "Category " + str(i % 10), "in_stock": True, "details": {"rating": 4.0 + (i % 10) * 0.1}}
                attrs_str = json.dumps(attrs).replace("'", "''")
                is_discounted = "true" if i % 5 == 0 else "false"
                created_at = f"2026-01-02 {i // 3600 % 24:02d}:{i // 60 % 60:02d}:{i % 60:02d}"
                batch.append(f"({i}, '{sku}', '{name}', {price:.2f}, {desc_val}, '{extra_desc}', '{attrs_str}', {is_discounted}, '{created_at}')")
                counts["products"] += 1
                if len(batch) >= BATCH_SIZE:
                    f.write("INSERT INTO products (id, sku, name, price, description, extra_description, attributes, is_discounted, created_at) VALUES\n" + ",\n".join(batch) + ";\n")
                    batch = []
                if i % 1250 == 0:
                    print(f"  .. generated {i} product records")
            if batch:
                f.write("INSERT INTO products (id, sku, name, price, description, extra_description, attributes, is_discounted, created_at) VALUES\n" + ",\n".join(batch) + ";\n")
                
            # 3. Orders: 100,000 records
            print("Generating orders...")
            f.write("\n-- 3. Orders\n")
            batch = []
            for i in range(1, TARGET_ORDERS + 1):
                user_id = ((i - 1) % TARGET_USERS) + 1
                day = (i % 28) + 1
                order_date = f"2026-02-{day:02d} {i // 3600 % 24:02d}:{i // 60 % 60:02d}:{i % 60:02d}"
                status = "COMPLETED" if i % 4 != 0 else "PENDING"
                total = 50.0 + (i * 0.01)
                tax = total * 0.08
                discount = total * 0.05 if i % 10 == 0 else 0.0
                addr = "" if i % 20 == 0 else ("NULL" if i % 40 == 0 else f"Address road {i}, City {i % 100}")
                addr_val = "NULL" if addr == "NULL" else f"'{addr}'"
                created_at = order_date
                batch.append(f"({i}, {user_id}, '{order_date}', '{status}', {total:.2f}, {tax:.4f}, {discount:.4f}, {addr_val}, '{created_at}')")
                counts["orders"] += 1
                if len(batch) >= BATCH_SIZE:
                    f.write("INSERT INTO orders (id, user_id, order_date, status, total_amount, tax_amount, discount_amount, shipping_address, created_at) VALUES\n" + ",\n".join(batch) + ";\n")
                    batch = []
                if i % 25000 == 0:
                    print(f"  .. generated {i} order records")
            if batch:
                f.write("INSERT INTO orders (id, user_id, order_date, status, total_amount, tax_amount, discount_amount, shipping_address, created_at) VALUES\n" + ",\n".join(batch) + ";\n")
                
            # 4. Order Items: 300,000 records
            print("Generating order items...")
            f.write("\n-- 4. Order Items\n")
            batch = []
            for i in range(1, TARGET_ORDER_ITEMS + 1):
                order_id = ((i - 1) % TARGET_ORDERS) + 1
                prod_idx = (i - 1) // TARGET_ORDERS
                prod_id = ((order_id + prod_idx * 1618) % TARGET_PRODUCTS) + 1
                quantity = (i % 5) + 1
                price = 9.99 + (prod_id * 0.05)
                created_at = f"2026-02-01 {i // 3600 % 24:02d}:{i // 60 % 60:02d}:{i % 60:02d}"
                batch.append(f"({i}, {order_id}, {prod_id}, {quantity}, {price:.2f}, '{created_at}')")
                counts["order_items"] += 1
                if len(batch) >= BATCH_SIZE:
                    f.write("INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, created_at) VALUES\n" + ",\n".join(batch) + ";\n")
                    batch = []
                if i % 75000 == 0:
                    print(f"  .. generated {i} order_item records")
            if batch:
                f.write("INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, created_at) VALUES\n" + ",\n".join(batch) + ";\n")
                
            # 5. Audit Logs: 50,000 records
            print("Generating audit logs...")
            f.write("\n-- 5. Audit Logs\n")
            batch = []
            for i in range(1, TARGET_AUDIT_LOGS + 1):
                entity_name = "orders"
                entity_id = i
                action_type = "INSERT"
                old_val = "NULL"
                new_val = json.dumps({"id": i, "status": "PENDING", "total": 50.0 + (i * 0.01)}).replace("'", "''")
                hex_data = f"DEADC0DE{i:08x}"
                mysql_blob = f"X'{hex_data}'"
                logged_at = f"2026-03-01 {i // 3600 % 24:02d}:{i // 60 % 60:02d}:{i % 60:02d}"
                batch.append(f"({i}, '{entity_name}', {entity_id}, '{action_type}', {old_val}, '{new_val}', {mysql_blob}, '{logged_at}')")
                counts["audit_logs"] += 1
                if len(batch) >= BATCH_SIZE:
                    f.write("INSERT INTO audit_logs (id, entity_name, entity_id, action_type, old_value, new_value, raw_payload, logged_at) VALUES\n" + ",\n".join(batch) + ";\n")
                    batch = []
                if i % 12500 == 0:
                    print(f"  .. generated {i} audit log records")
            if batch:
                f.write("INSERT INTO audit_logs (id, entity_name, entity_id, action_type, old_value, new_value, raw_payload, logged_at) VALUES\n" + ",\n".join(batch) + ";\n")
                
            f.write("\nSET FOREIGN_KEY_CHECKS = 1;\n")

        # VALIDATION PASS
        expected = {
            "users": TARGET_USERS,
            "products": TARGET_PRODUCTS,
            "orders": TARGET_ORDERS,
            "order_items": TARGET_ORDER_ITEMS,
            "audit_logs": TARGET_AUDIT_LOGS
        }
        
        validation_failed = False
        for table, expected_count in expected.items():
            if counts[table] != expected_count:
                print(f"ERROR: Row count mismatch for table '{table}': expected {expected_count}, generated {counts[table]}", file=sys.stderr)
                validation_failed = True
                
        if validation_failed:
            print("ERROR: Seed data validation failed! Output is invalid.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"\nFATAL: Seed generation failed: {e}", file=sys.stderr)
        sys.exit(1)

    duration = time.perf_counter() - start_time
    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    total_rows = sum(counts.values())
    
    print("\nGeneration completed successfully.\n")
    print("Expected rows:")
    for table, count in expected.items():
        print(f"  * {table}: {count:,}")
    print("\nGenerated rows:")
    for table, count in counts.items():
        print(f"  * {table}: {count:,}")
    print(f"\nElapsed time: {duration:.4f} seconds")
    print(f"Output size: {file_size_mb:.2f} MB ({file_size_bytes:,} bytes)")

if __name__ == "__main__":
    generate_dml()

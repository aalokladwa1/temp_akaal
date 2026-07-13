# -*- coding: utf-8 -*-
"""
Akaal Data Generator
Generates sample_data.sql with deterministic, valid SQL statements
for both MySQL and PostgreSQL dialects.
"""

import os
import json

def generate_dml():
    mysql_dml = []
    postgres_dml = []

    # 1. Users (100)
    for i in range(1, 101):
        email = f"user_{i}@example.com"
        name = f"User Name {i}"
        is_active = "TRUE" if i % 10 != 0 else "FALSE"
        created_at = f"2026-01-01 10:{i//60:02d}:{i%60:02d}"
        
        mysql_dml.append(
            f"INSERT INTO users (id, email, full_name, is_active, created_at) "
            f"VALUES ({i}, '{email}', '{name}', {is_active}, '{created_at}');"
        )
        postgres_dml.append(
            f"INSERT INTO users (id, email, full_name, is_active, created_at) "
            f"VALUES ({i}, '{email}', '{name}', {is_active}, '{created_at}');"
        )

    # 2. Products (200)
    for i in range(1, 201):
        sku = f"SKU-PROD-{i:03d}"
        name = f"Product Item {i}"
        price = 9.99 + (i * 0.5)
        desc = f"Detailed description for product number {i} with extended details."
        attrs = {"id": i, "category": "General", "in_stock": True, "details": {"rating": 4.5}}
        attrs_str = json.dumps(attrs)
        created_at = f"2026-01-02 08:{i//60:02d}:{i%60:02d}"

        mysql_dml.append(
            f"INSERT INTO products (id, sku, name, price, description, attributes, created_at) "
            f"VALUES ({i}, '{sku}', '{name}', {price:.2f}, '{desc}', '{attrs_str}', '{created_at}');"
        )
        postgres_dml.append(
            f"INSERT INTO products (id, sku, name, price, description, attributes, created_at) "
            f"VALUES ({i}, '{sku}', '{name}', {price:.2f}, '{desc}', '{attrs_str}'::jsonb, '{created_at}');"
        )

    # 3. Orders (1000)
    for i in range(1, 1001):
        user_id = ((i - 1) % 100) + 1
        day = (i % 28) + 1
        order_date = f"2026-02-{day:02d}"
        status = "COMPLETED" if i % 5 != 0 else "PENDING"
        total = 50.0 + (i * 0.1)
        created_at = f"{order_date} 09:00:00"

        mysql_dml.append(
            f"INSERT INTO orders (id, user_id, order_date, status, total_amount, created_at) "
            f"VALUES ({i}, {user_id}, '{order_date}', '{status}', {total:.2f}, '{created_at}');"
        )
        postgres_dml.append(
            f"INSERT INTO orders (id, user_id, order_date, status, total_amount, created_at) "
            f"VALUES ({i}, {user_id}, '{order_date}', '{status}', {total:.2f}, '{created_at}');"
        )

    # 4. Order Items (3000)
    for i in range(1, 3001):
        order_id = ((i - 1) % 1000) + 1
        prod_id = ((i - 1) % 200) + 1
        quantity = (i % 5) + 1
        price = 9.99 + (prod_id * 0.5)

        mysql_dml.append(
            f"INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) "
            f"VALUES ({i}, {order_id}, {prod_id}, {quantity}, {price:.2f});"
        )
        postgres_dml.append(
            f"INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) "
            f"VALUES ({i}, {order_id}, {prod_id}, {quantity}, {price:.2f});"
        )

    # 5. Audit Logs (500)
    for i in range(1, 501):
        entity_name = "orders"
        entity_id = i
        action_type = "INSERT"
        old_val = "NULL"
        new_val = json.dumps({"id": i, "status": "PENDING", "total": 50.0 + (i * 0.1)})
        
        # Hex representation for binary payload: "DEADC0DE" followed by index hex
        hex_data = f"DEADC0DE{i:08x}"
        mysql_blob = f"X'{hex_data}'"
        postgres_blob = f"'\\x{hex_data}'::bytea"
        logged_at = f"2026-03-01 12:00:00"

        mysql_dml.append(
            f"INSERT INTO audit_logs (id, entity_name, entity_id, action_type, old_value, new_value, raw_payload, logged_at) "
            f"VALUES ({i}, '{entity_name}', {entity_id}, '{action_type}', {old_val}, '{new_val}', {mysql_blob}, '{logged_at}');"
        )
        postgres_dml.append(
            f"INSERT INTO audit_logs (id, entity_name, entity_id, action_type, old_value, new_value, raw_payload, logged_at) "
            f"VALUES ({i}, '{entity_name}', {entity_id}, '{action_type}', {old_val}::jsonb, '{new_val}'::jsonb, {postgres_blob}, '{logged_at}');"
        )

    # Combine into sql file
    with open("tests/integration/sample_data.sql", "w", encoding="utf-8") as f:
        f.write("-- ======================================================================\n")
        f.write("-- Akaal Smoke Test Seed Data DML\n")
        f.write("-- ======================================================================\n\n")
        
        f.write("-- [MYSQL_START]\n")
        f.write("\n".join(mysql_dml))
        f.write("\n-- [MYSQL_END]\n\n")

        f.write("-- [POSTGRES_START]\n")
        f.write("\n".join(postgres_dml))
        f.write("\n-- [POSTGRES_END]\n")

    print("Successfully generated sample_data.sql")

if __name__ == "__main__":
    generate_dml()

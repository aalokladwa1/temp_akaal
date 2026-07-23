"""
AKAAL Medium-Scale Migration — Step 1: Provision 50-table, 100,000+ row source dataset in PostgreSQL.
"""

import sys
import os
import io
import time
import uuid
import datetime
import random
import psycopg2
import psycopg2.extras

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PG_DSN = dict(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='postgres')

UNICODE_NAMES = [
    ('Alice', 'Smith', 'US'),
    ('Bob', 'Müller', 'DE'),
    ('Chloé', 'Dupont', 'FR'),
    ('Dmitri', 'Иванов', 'RU'),
    ('Emiko', '田中', 'JP'),
    ('Frank', "O'Brien", 'IE'),
    ('Giulia', 'Rossi', 'IT'),
    ('Hiroshi', '鈴木', 'JP'),
    ('Ingrid', 'Lindqvist', 'SE'),
    ('João', 'Silva', 'BR'),
]

CATEGORIES = ['Electronics', 'Peripherals', 'Storage', 'Accessories', 'Furniture', 'Networking', 'Software', 'Services', 'Mobile', 'Gaming']

def provision():
    print("=================================================================")
    print("   PROVISIONING MEDIUM-SCALE SOURCE DATASET IN POSTGRESQL")
    print("=================================================================")

    conn = psycopg2.connect(**PG_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    # Drop existing medium schema / tables in public if present
    print("Cleaning up old test tables...")
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    tables = [r[0] for r in cur.fetchall()]
    if tables:
        cur.execute(f"DROP TABLE IF EXISTS {', '.join(tables)} CASCADE;")
    conn.commit()

    print("\n[1/4] Creating 50 schema DDL statements with constraints & indexes...")
    ddl_statements = []

    # Level 1: Core Master Tables (1-10)
    ddl_statements.append("""
        CREATE TABLE core_departments (
            dept_id SERIAL PRIMARY KEY,
            dept_code VARCHAR(20) UNIQUE NOT NULL,
            dept_name VARCHAR(100) NOT NULL,
            budget NUMERIC(14,2) DEFAULT 100000.00,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX idx_dept_code ON core_departments(dept_code);
    """)

    ddl_statements.append("""
        CREATE TABLE core_regions (
            region_id SERIAL PRIMARY KEY,
            region_name VARCHAR(50) UNIQUE NOT NULL,
            country_code CHAR(2) NOT NULL,
            tax_rate NUMERIC(5,4) DEFAULT 0.0500,
            notes TEXT
        );
    """)

    ddl_statements.append("""
        CREATE TABLE core_currencies (
            currency_code CHAR(3) PRIMARY KEY,
            currency_name VARCHAR(50) NOT NULL,
            symbol VARCHAR(5) NOT NULL,
            exchange_rate NUMERIC(10,6) DEFAULT 1.000000
        );
    """)

    ddl_statements.append("""
        CREATE TABLE core_system_logs (
            log_id BIGSERIAL PRIMARY KEY,
            log_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
            severity VARCHAR(10) NOT NULL,
            message TEXT NOT NULL,
            payload_blob BYTEA,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT chk_severity CHECK (severity IN ('INFO','WARN','ERROR','FATAL'))
        );
        CREATE INDEX idx_syslog_severity ON core_system_logs(severity);
    """)

    for i in range(5, 11):
        ddl_statements.append(f"""
            CREATE TABLE core_master_{i} (
                master_id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                title VARCHAR(150) NOT NULL,
                status VARCHAR(20) DEFAULT 'ACTIVE',
                val_numeric NUMERIC(12,4) DEFAULT 0.0000,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

    # Level 2: Entity Tables with Level 1 FKs (11-20)
    ddl_statements.append("""
        CREATE TABLE org_employees (
            emp_id SERIAL PRIMARY KEY,
            dept_id INT NOT NULL REFERENCES core_departments(dept_id),
            region_id INT NOT NULL REFERENCES core_regions(region_id),
            ext_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
            first_name VARCHAR(80) NOT NULL,
            last_name VARCHAR(80) NOT NULL,
            email VARCHAR(200) UNIQUE NOT NULL,
            salary NUMERIC(12,2) NOT NULL,
            hire_date DATE NOT NULL,
            is_manager BOOLEAN DEFAULT FALSE,
            bio TEXT,
            avatar_blob BYTEA,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX idx_emp_dept ON org_employees(dept_id);
        CREATE INDEX idx_emp_email ON org_employees(email);
    """)

    ddl_statements.append("""
        CREATE TABLE catalog_vendors (
            vendor_id SERIAL PRIMARY KEY,
            region_id INT NOT NULL REFERENCES core_regions(region_id),
            vendor_name VARCHAR(150) NOT NULL,
            contact_email VARCHAR(200) NOT NULL,
            rating NUMERIC(3,2) DEFAULT 5.00,
            is_certified BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    for i in range(13, 21):
        ddl_statements.append(f"""
            CREATE TABLE entity_level2_{i} (
                entity_id SERIAL PRIMARY KEY,
                dept_id INT NOT NULL REFERENCES core_departments(dept_id),
                ref_code VARCHAR(50) NOT NULL,
                label VARCHAR(150) NOT NULL,
                is_valid BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

    # Level 3: Transactional & Composite Key Tables (21-30)
    ddl_statements.append("""
        CREATE TABLE catalog_products (
            product_id SERIAL PRIMARY KEY,
            vendor_id INT NOT NULL REFERENCES catalog_vendors(vendor_id),
            sku VARCHAR(50) UNIQUE NOT NULL,
            product_name VARCHAR(200) NOT NULL,
            category VARCHAR(80) NOT NULL,
            unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
            stock_qty INT NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX idx_prod_sku ON catalog_products(sku);
        CREATE INDEX idx_prod_category ON catalog_products(category);
    """)

    # Composite PK table
    ddl_statements.append("""
        CREATE TABLE org_employee_skills (
            emp_id INT NOT NULL REFERENCES org_employees(emp_id),
            skill_name VARCHAR(50) NOT NULL,
            proficiency_level INT NOT NULL CHECK (proficiency_level BETWEEN 1 AND 5),
            certified_date DATE,
            PRIMARY KEY (emp_id, skill_name)
        );
    """)

    for i in range(23, 31):
        ddl_statements.append(f"""
            CREATE TABLE transaction_level3_{i} (
                tx_id BIGSERIAL PRIMARY KEY,
                emp_id INT NOT NULL REFERENCES org_employees(emp_id),
                amount NUMERIC(12,2) NOT NULL,
                status VARCHAR(20) DEFAULT 'COMPLETED',
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

    # Level 4: Sales & Orders Hierarchy (31-40)
    ddl_statements.append("""
        CREATE TABLE sales_customers (
            customer_id SERIAL PRIMARY KEY,
            region_id INT NOT NULL REFERENCES core_regions(region_id),
            ext_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
            first_name VARCHAR(80) NOT NULL,
            last_name VARCHAR(80) NOT NULL,
            email VARCHAR(200) UNIQUE NOT NULL,
            credit_limit NUMERIC(12,2) DEFAULT 1000.00,
            is_vip BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX idx_cust_email ON sales_customers(email);
    """)

    ddl_statements.append("""
        CREATE TABLE sales_orders (
            order_id BIGSERIAL PRIMARY KEY,
            customer_id INT NOT NULL REFERENCES sales_customers(customer_id),
            emp_id INT NOT NULL REFERENCES org_employees(emp_id),
            currency_code CHAR(3) NOT NULL REFERENCES core_currencies(currency_code),
            order_date DATE NOT NULL DEFAULT CURRENT_DATE,
            total_amount NUMERIC(14,2) NOT NULL DEFAULT 0.00,
            order_status VARCHAR(20) DEFAULT 'PENDING' CHECK (order_status IN ('PENDING','CONFIRMED','SHIPPED','DELIVERED','CANCELLED')),
            placed_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX idx_order_cust ON sales_orders(customer_id);
        CREATE INDEX idx_order_date ON sales_orders(order_date);
    """)

    for i in range(33, 41):
        ddl_statements.append(f"""
            CREATE TABLE sales_level4_{i} (
                id BIGSERIAL PRIMARY KEY,
                customer_id INT NOT NULL REFERENCES sales_customers(customer_id),
                ref_num VARCHAR(50) NOT NULL,
                val NUMERIC(10,2) DEFAULT 0.00,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

    # Level 5: Detailed Line Items & Audits (41-50)
    ddl_statements.append("""
        CREATE TABLE sales_order_items (
            item_id BIGSERIAL PRIMARY KEY,
            order_id BIGINT NOT NULL REFERENCES sales_orders(order_id),
            product_id INT NOT NULL REFERENCES catalog_products(product_id),
            quantity INT NOT NULL CHECK (quantity > 0),
            unit_price NUMERIC(10,2) NOT NULL,
            discount_pct NUMERIC(5,2) DEFAULT 0.00 CHECK (discount_pct BETWEEN 0 AND 100),
            line_total NUMERIC(12,2) NOT NULL,
            CONSTRAINT uq_order_item_prod UNIQUE (order_id, product_id)
        );
        CREATE INDEX idx_order_items_order ON sales_order_items(order_id);
    """)

    # Composite FK table
    ddl_statements.append("""
        CREATE TABLE sales_order_audit (
            audit_id BIGSERIAL PRIMARY KEY,
            order_id BIGINT NOT NULL REFERENCES sales_orders(order_id),
            action VARCHAR(50) NOT NULL,
            performed_by VARCHAR(100) NOT NULL,
            audit_timestamp TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    for i in range(43, 51):
        ddl_statements.append(f"""
            CREATE TABLE audit_level5_{i} (
                audit_id BIGSERIAL PRIMARY KEY,
                order_id BIGINT NOT NULL REFERENCES sales_orders(order_id),
                log_msg TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

    for stmt in ddl_statements:
        cur.execute(stmt)
    conn.commit()
    print("  [OK] 50 Tables created successfully.")

    # Populate Data
    print("\n[2/4] Populating core master tables...")
    
    # Core Currencies
    currencies = [('USD', 'US Dollar', '$', 1.0), ('EUR', 'Euro', '€', 0.92), ('JPY', 'Japanese Yen', '¥', 155.0), ('GBP', 'British Pound', '£', 0.79), ('CAD', 'Canadian Dollar', '$', 1.36)]
    cur.executemany("INSERT INTO core_currencies VALUES (%s, %s, %s, %s);", currencies)

    # Core Regions
    regions = [('North America', 'US', 0.0700, 'Main NA region'), ('Europe Central', 'DE', 0.1900, 'EU HQ'), ('Asia Pacific', 'JP', 0.1000, 'APAC branch'), ('Latin America', 'BR', 0.1200, 'LATAM branch'), ('UK & Ireland', 'GB', 0.2000, 'UK branch')]
    cur.executemany("INSERT INTO core_regions (region_name, country_code, tax_rate, notes) VALUES (%s, %s, %s, %s);", regions)

    # Core Departments
    depts = [('ENG', 'Engineering', 5000000.00), ('SLS', 'Sales', 3000000.00), ('MKT', 'Marketing', 1500000.00), ('FIN', 'Finance', 2000000.00), ('HR', 'Human Resources', 1000000.00)]
    cur.executemany("INSERT INTO core_departments (dept_code, dept_name, budget) VALUES (%s, %s, %s);", depts)

    # Populate master tables 5-10
    for i in range(5, 11):
        rows = [(f"CODE_{i}_{j}", f"Master Title {i}-{j}", "ACTIVE", j * 12.34) for j in range(1, 101)]
        psycopg2.extras.execute_batch(cur, f"INSERT INTO core_master_{i} (code, title, status, val_numeric) VALUES (%s, %s, %s, %s);", rows)

    # Populate system logs
    log_rows = [
        (f"LOG-{k}", 'INFO' if k % 4 != 0 else 'ERROR', f"System status log entry #{k}", psycopg2.Binary(b"BINARY_PAYLOAD_SAMPLE_DATA"))
        for k in range(1, 2001)
    ]
    psycopg2.extras.execute_batch(cur, "INSERT INTO core_system_logs (severity, message, payload_blob) VALUES (%s, %s, %s);", [(r[1], r[2], r[3]) for r in log_rows])

    conn.commit()
    print("  [OK] Core master tables populated.")

    print("\n[3/4] Populating Employees, Customers, Vendors & Products...")
    # Employees (1,000 employees)
    emp_data = []
    for k in range(1, 1001):
        fn, ln, country = UNICODE_NAMES[k % len(UNICODE_NAMES)]
        email = f"emp_{k}.{fn.lower()}@akaal-enterprise.com"
        salary = 40000.00 + (k * 75.50)
        hdate = datetime.date(2020, 1, 1) + datetime.timedelta(days=k % 1500)
        bio = f"Employee {fn} {ln} based in {country}. Specializing in enterprise migration systems."
        blob = psycopg2.Binary(f"AVATAR_BLOB_{k}".encode('utf-8'))
        emp_data.append(( (k % 5) + 1, (k % 5) + 1, fn, ln, email, salary, hdate, k % 10 == 0, bio, blob ))
    
    psycopg2.extras.execute_batch(cur, """
        INSERT INTO org_employees (dept_id, region_id, first_name, last_name, email, salary, hire_date, is_manager, bio, avatar_blob)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, emp_data)

    # Employee Skills (Composite PK: 2,000 skills)
    skills = ['Python', 'SQL', 'PostgreSQL', 'MySQL', 'Docker', 'Kubernetes', 'AWS', 'Java', 'Go', 'Rust']
    skill_rows = [(emp_id, skill, random.randint(1, 5), datetime.date(2022, 1, 1)) for emp_id in range(1, 1001) for skill in random.sample(skills, 2)]
    psycopg2.extras.execute_batch(cur, "INSERT INTO org_employee_skills (emp_id, skill_name, proficiency_level, certified_date) VALUES (%s, %s, %s, %s);", skill_rows)

    # Vendors (500 vendors)
    vendor_rows = [( (k % 5) + 1, f"Vendor {k} Corp", f"vendor_{k}@supplier.org", 4.50, True) for k in range(1, 501)]
    psycopg2.extras.execute_batch(cur, "INSERT INTO catalog_vendors (region_id, vendor_name, contact_email, rating, is_certified) VALUES (%s, %s, %s, %s, %s);", vendor_rows)

    # Products (2,000 products)
    product_rows = [
        ( (k % 500) + 1, f"SKU-{k:05d}", f"Enterprise Product {k}", CATEGORIES[k % len(CATEGORIES)], 19.99 + (k * 2.5), 100 + k )
        for k in range(1, 2001)
    ]
    psycopg2.extras.execute_batch(cur, "INSERT INTO catalog_products (vendor_id, sku, product_name, category, unit_price, stock_qty) VALUES (%s, %s, %s, %s, %s, %s);", product_rows)

    # Customers (5,000 customers)
    cust_data = []
    for k in range(1, 5001):
        fn, ln, country = UNICODE_NAMES[k % len(UNICODE_NAMES)]
        email = f"customer_{k}_{fn.lower()}@domain.com"
        limit = 1000.00 + (k * 10.0)
        cust_data.append(( (k % 5) + 1, fn, ln, email, limit, k % 5 == 0 ))

    psycopg2.extras.execute_batch(cur, "INSERT INTO sales_customers (region_id, first_name, last_name, email, credit_limit, is_vip) VALUES (%s, %s, %s, %s, %s, %s);", cust_data)

    # Populate entity level 2 and transaction level 3 tables (tables 13-30)
    for i in range(13, 21):
        rows = [((j % 5) + 1, f"REF_{i}_{j}", f"Level 2 Label {i}-{j}", True) for j in range(1, 501)]
        psycopg2.extras.execute_batch(cur, f"INSERT INTO entity_level2_{i} (dept_id, ref_code, label, is_valid) VALUES (%s, %s, %s, %s);", rows)

    for i in range(23, 31):
        rows = [((j % 1000) + 1, 100.00 + (j * 1.5), 'COMPLETED', f"Tx note {i}-{j}") for j in range(1, 1001)]
        psycopg2.extras.execute_batch(cur, f"INSERT INTO transaction_level3_{i} (emp_id, amount, status, notes) VALUES (%s, %s, %s, %s);", rows)

    conn.commit()
    print("  [OK] Employees, Customers, Vendors & Products populated.")

    print("\n[4/4] Generating 20,000 Sales Orders & 60,000 Order Items (Total Dataset > 100,000 Rows)...")
    
    # Sales Orders (20,000 orders)
    statuses = ['PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED']
    curr_codes = ['USD', 'EUR', 'JPY', 'GBP', 'CAD']
    order_data = [
        ( (k % 5000) + 1, (k % 1000) + 1, curr_codes[k % 5], datetime.date(2026, 1, 1) + datetime.timedelta(days=k % 180), (k * 15.50) % 5000.00, statuses[k % 5] )
        for k in range(1, 20001)
    ]
    psycopg2.extras.execute_batch(cur, "INSERT INTO sales_orders (customer_id, emp_id, currency_code, order_date, total_amount, order_status) VALUES (%s, %s, %s, %s, %s, %s);", order_data)

    # Sales Order Items (60,000 items - 3 per order)
    item_rows = []
    for o_id in range(1, 20001):
        for item_offset in range(1, 4):
            prod_id = ((o_id + item_offset * 500) % 2000) + 1
            qty = (o_id % 5) + 1
            price = 25.00 + (prod_id * 1.50)
            disc = 5.00 if o_id % 4 == 0 else 0.00
            line_tot = round(qty * price * (1 - disc / 100.0), 2)
            item_rows.append((o_id, prod_id, qty, price, disc, line_tot))

    psycopg2.extras.execute_batch(cur, "INSERT INTO sales_order_items (order_id, product_id, quantity, unit_price, discount_pct, line_total) VALUES (%s, %s, %s, %s, %s, %s);", item_rows)

    # Sales Level 4 (tables 33-40) - 2,000 rows each = 16,000 rows
    for i in range(33, 41):
        rows = [((j % 5000) + 1, f"REF4_{i}_{j}", j * 5.25) for j in range(1, 2001)]
        psycopg2.extras.execute_batch(cur, f"INSERT INTO sales_level4_{i} (customer_id, ref_num, val) VALUES (%s, %s, %s);", rows)

    # Sales Order Audit & Level 5 Audit (tables 42-50) - 1,000 rows each = 9,000 rows
    audit_actions = ['CREATED', 'PAYMENT_RECEIVED', 'SHIPPED', 'DELIVERED', 'UPDATED']
    audit_rows = [((j % 20000) + 1, audit_actions[j % 5], f"user_{j % 50}") for j in range(1, 2001)]
    psycopg2.extras.execute_batch(cur, "INSERT INTO sales_order_audit (order_id, action, performed_by) VALUES (%s, %s, %s);", audit_rows)

    for i in range(43, 51):
        rows = [((j % 20000) + 1, f"Audit log event {i}-{j} recorded successfully.") for j in range(1, 1001)]
        psycopg2.extras.execute_batch(cur, f"INSERT INTO audit_level5_{i} (order_id, log_msg) VALUES (%s, %s);", rows)

    # Create Views
    cur.execute("""
        CREATE VIEW view_customer_order_summary AS
        SELECT c.customer_id, c.first_name, c.last_name, c.email, COUNT(o.order_id) as total_orders, COALESCE(SUM(o.total_amount), 0.00) as lifetime_value
        FROM sales_customers c
        LEFT JOIN sales_orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.first_name, c.last_name, c.email;
    """)

    conn.commit()

    # Calculate Total Row Count
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
    all_tables = [r[0] for r in cur.fetchall()]
    total_rows = 0
    table_counts = {}
    for t in all_tables:
        cur.execute(f"SELECT COUNT(*) FROM {t};")
        cnt = cur.fetchone()[0]
        table_counts[t] = cnt
        total_rows += cnt

    conn.close()

    print("\n=================================================================")
    print("           MEDIUM-SCALE SOURCE DATASET PROVISIONED")
    print("=================================================================")
    print(f"  Total Tables Created:  {len(all_tables)}")
    print(f"  Total Dataset Rows:    {total_rows:,}")
    print(f"  Hierarchy Levels:      5")
    print(f"  Views Created:         1 (view_customer_order_summary)")
    print("=================================================================\n")

if __name__ == '__main__':
    provision()

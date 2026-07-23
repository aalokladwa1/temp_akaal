"""
AKAAL Smoke Migration — Step 1: Provision source schema in PostgreSQL.

Creates a realistic 4-table e-commerce database with:
  - Primary keys, foreign keys, indexes, constraints
  - Various data types: INTEGER, BIGINT, NUMERIC, VARCHAR, TEXT, BOOLEAN,
    TIMESTAMP WITH TIME ZONE, DATE, UUID, JSON
  - NULL values, Unicode text, timestamps
  - 100-1000 rows spread across tables
"""
import psycopg2
import psycopg2.extras
import datetime
import decimal
import uuid

PG_DSN = dict(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='postgres')

DDL = """
DROP SCHEMA IF EXISTS smoke_src CASCADE;
CREATE SCHEMA smoke_src;

-- ─── CUSTOMERS ─────────────────────────────────────────────────────────────
CREATE TABLE smoke_src.customers (
    customer_id   SERIAL        PRIMARY KEY,
    ext_uuid      UUID          NOT NULL DEFAULT gen_random_uuid(),
    first_name    VARCHAR(80)   NOT NULL,
    last_name     VARCHAR(80)   NOT NULL,
    email         VARCHAR(200)  NOT NULL UNIQUE,
    phone         VARCHAR(30),
    country_code  CHAR(2)       NOT NULL DEFAULT 'US',
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    credit_limit  NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    notes         TEXT,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_customers_email    ON smoke_src.customers (email);
CREATE INDEX idx_customers_country  ON smoke_src.customers (country_code);

-- ─── PRODUCTS ──────────────────────────────────────────────────────────────
CREATE TABLE smoke_src.products (
    product_id    SERIAL        PRIMARY KEY,
    sku           VARCHAR(50)   NOT NULL UNIQUE,
    name          VARCHAR(200)  NOT NULL,
    description   TEXT,
    category      VARCHAR(80)   NOT NULL,
    unit_price    NUMERIC(10,2) NOT NULL,
    weight_kg     NUMERIC(8,3),
    is_available  BOOLEAN       NOT NULL DEFAULT TRUE,
    stock_qty     INTEGER       NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_price_positive CHECK (unit_price >= 0),
    CONSTRAINT chk_stock_nonneg   CHECK (stock_qty  >= 0)
);
CREATE INDEX idx_products_sku      ON smoke_src.products (sku);
CREATE INDEX idx_products_category ON smoke_src.products (category);

-- ─── ORDERS ────────────────────────────────────────────────────────────────
CREATE TABLE smoke_src.orders (
    order_id      BIGSERIAL     PRIMARY KEY,
    customer_id   INTEGER       NOT NULL REFERENCES smoke_src.customers(customer_id),
    order_date    DATE          NOT NULL DEFAULT CURRENT_DATE,
    status        VARCHAR(20)   NOT NULL DEFAULT 'PENDING',
    currency      CHAR(3)       NOT NULL DEFAULT 'USD',
    total_amount  NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    shipping_addr TEXT,
    placed_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_order_status CHECK (status IN ('PENDING','CONFIRMED','SHIPPED','DELIVERED','CANCELLED'))
);
CREATE INDEX idx_orders_customer   ON smoke_src.orders (customer_id);
CREATE INDEX idx_orders_date       ON smoke_src.orders (order_date);
CREATE INDEX idx_orders_status     ON smoke_src.orders (status);

-- ─── ORDER_ITEMS ───────────────────────────────────────────────────────────
CREATE TABLE smoke_src.order_items (
    item_id       BIGSERIAL     PRIMARY KEY,
    order_id      BIGINT        NOT NULL REFERENCES smoke_src.orders(order_id),
    product_id    INTEGER       NOT NULL REFERENCES smoke_src.products(product_id),
    quantity      INTEGER       NOT NULL,
    unit_price    NUMERIC(10,2) NOT NULL,
    discount_pct  NUMERIC(5,2)  NOT NULL DEFAULT 0.00,
    line_total    NUMERIC(12,2) GENERATED ALWAYS AS (
                      quantity * unit_price * (1 - discount_pct / 100)
                  ) STORED,
    CONSTRAINT chk_qty_positive      CHECK (quantity     > 0),
    CONSTRAINT chk_discount_range    CHECK (discount_pct BETWEEN 0 AND 100),
    UNIQUE (order_id, product_id)
);
CREATE INDEX idx_order_items_order   ON smoke_src.order_items (order_id);
CREATE INDEX idx_order_items_product ON smoke_src.order_items (product_id);
"""

CUSTOMERS = [
    # (first_name, last_name, email, phone, country_code, is_active, credit_limit, notes)
    ('Alice',   'Smith',    'alice.smith@example.com',   '+1-555-0101', 'US', True,  5000.00, 'VIP customer'),
    ('Bob',     'Müller',   'bob.muller@example.de',     '+49-30-5550', 'DE', True,  2000.00, 'German client — Büro Berlin'),
    ('Chloé',   'Dupont',   'chloe.dupont@example.fr',  '+33-1-5550',  'FR', True,  3500.00, None),
    ('Dmitri',  'Иванов',   'dmitri.ivanov@example.ru', '+7-495-5550', 'RU', False,    0.00, 'Account suspended'),
    ('Emiko',   '田中',     'emiko.tanaka@example.jp',  '+81-3-5550',  'JP', True,  8000.00, '日本語テスト'),
    ('Frank',   "O'Brien",  'frank.obrien@example.ie',   None,          'IE', True,  1500.00, None),
    ('Giulia',  'Rossi',    'giulia.rossi@example.it',  '+39-02-5550', 'IT', True,  2500.00, 'Preferisce fattura'),
    ('Hiroshi', '鈴木',     'hiroshi.suzuki@example.jp','+81-6-5550',  'JP', True,  4000.00, None),
    ('Ingrid',  'Lindqvist','ingrid.lindqvist@example.se','+46-8-5550','SE', True,  3000.00, 'SEK payments'),
    ('João',    'Silva',    'joao.silva@example.br',     None,          'BR', True,   500.00, None),
]

PRODUCTS = [
    # (sku, name, description, category, unit_price, weight_kg, is_available, stock_qty)
    ('LAPTOP-001', 'ProBook 15 Laptop', '15" QHD, 32GB RAM, 1TB NVMe', 'Electronics', 1299.99, 2.100, True,  45),
    ('MOUSE-001',  'Ergonomic Mouse',   'Wireless, 2400 DPI',           'Peripherals',    49.99, 0.145, True, 230),
    ('KB-001',     'Mechanical Keyboard','TKL, Cherry MX Blue',         'Peripherals',   129.99, 0.920, True,  88),
    ('MONITOR-001','27" 4K Display',    '3840×2160, IPS, HDR400',       'Electronics',   549.99, 7.500, True,  17),
    ('WEBCAM-001', 'HD Webcam 1080p',   'Built-in noise-cancelling mic','Peripherals',    79.99, 0.280, True, 162),
    ('HDMI-001',   'HDMI 2.1 Cable 2m', '8K@60Hz certified',           'Accessories',    19.99, 0.085, True, 400),
    ('USB-HUB-001','USB-C Hub 7-in-1',  '100W PD, 4K HDMI, SD reader', 'Accessories',    59.99, 0.220, True,  95),
    ('SSD-001',    '1TB External SSD',  'USB-C, 1050MB/s read',        'Storage',       109.99, 0.058, True,  73),
    ('BAG-001',    'Laptop Backpack',   'Water-resistant, 30L capacity','Accessories',    89.99, 0.650, True,  51),
    ('CHAIR-001',  'Ergonomic Chair',   'Lumbar support, mesh back',    'Furniture',     399.99,19.800, False,  0),
]

# Orders: 1 per customer (10 orders)
ORDERS = [
    # (customer_idx 0-based, order_date, status, currency, total_amount, shipping_addr)
    (0, '2026-01-15', 'DELIVERED', 'USD', 1429.97, '123 Main St, New York, NY 10001, USA'),
    (1, '2026-02-03', 'DELIVERED', 'EUR',  179.98, 'Unter den Linden 10, 10117 Berlin, DE'),
    (2, '2026-02-20', 'SHIPPED',   'EUR',  549.99, '15 Rue de la Paix, 75001 Paris, FR'),
    (3, '2026-03-01', 'CANCELLED', 'USD',    0.00, None),
    (4, '2026-03-10', 'DELIVERED', 'JPY', 8000.00, '1-1 Shinjuku, Tokyo 160-0022, JP'),
    (5, '2026-04-05', 'CONFIRMED', 'EUR',  219.97, '10 O\'Connell St, Dublin 1, IE'),
    (6, '2026-04-18', 'PENDING',   'EUR',  109.99, 'Via Roma 1, 20121 Milano, IT'),
    (7, '2026-05-02', 'DELIVERED', 'JPY', 4000.00, '3-3 Namba, Osaka 542-0076, JP'),
    (8, '2026-05-20', 'SHIPPED',   'SEK', 3000.00, 'Drottninggatan 1, 111 51 Stockholm, SE'),
    (9, '2026-06-01', 'PENDING',   'BRL',  500.00, 'Av. Paulista 1000, São Paulo - SP, BR'),
]

# Order items: (order_idx 0-based, product_idx 0-based, quantity, unit_price, discount_pct)
ORDER_ITEMS = [
    (0, 0, 1, 1299.99, 0.00),   # Order 1: Laptop
    (0, 1, 2,   49.99, 0.00),   # Order 1: 2x Mouse
    (0, 2, 1,  129.99,10.00),   # Order 1: Keyboard -10%
    (1, 1, 1,   49.99, 0.00),   # Order 2: Mouse
    (1, 5, 3,   19.99, 0.00),   # Order 2: 3x HDMI
    (2, 3, 1,  549.99, 0.00),   # Order 3: Monitor
    # Order 4: cancelled — no items
    (4, 4, 1,   79.99, 0.00),   # Order 5: Webcam
    (4, 6, 1,   59.99, 0.00),   # Order 5: USB Hub
    (5, 2, 1,  129.99, 0.00),   # Order 6: Keyboard
    (5, 5, 2,   19.99,50.00),   # Order 6: 2x HDMI -50%
    (5, 1, 1,   49.99, 0.00),   # Order 6: Mouse
    (6, 7, 1,  109.99, 0.00),   # Order 7: SSD
    (7, 4, 1,   79.99, 0.00),   # Order 8: Webcam (JPY order, price same numeric)
    (8, 8, 1,   89.99, 0.00),   # Order 9: Bag
    (8, 5, 3,   19.99,20.00),   # Order 9: 3x HDMI -20%
    (9, 8, 1,   89.99, 0.00),   # Order 10: Bag
]


def provision():
    conn = psycopg2.connect(**PG_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    # Create schema + tables
    cur.execute(DDL)

    # Insert customers
    cust_ids = []
    for row in CUSTOMERS:
        cur.execute("""
            INSERT INTO smoke_src.customers
              (first_name,last_name,email,phone,country_code,is_active,credit_limit,notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING customer_id
        """, row)
        cust_ids.append(cur.fetchone()[0])
    print(f'Inserted {len(cust_ids)} customers')

    # Insert products
    prod_ids = []
    for row in PRODUCTS:
        cur.execute("""
            INSERT INTO smoke_src.products
              (sku,name,description,category,unit_price,weight_kg,is_available,stock_qty)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING product_id
        """, row)
        prod_ids.append(cur.fetchone()[0])
    print(f'Inserted {len(prod_ids)} products')

    # Insert orders
    order_ids = []
    for (cidx, odate, status, currency, total, addr) in ORDERS:
        cur.execute("""
            INSERT INTO smoke_src.orders
              (customer_id,order_date,status,currency,total_amount,shipping_addr)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING order_id
        """, (cust_ids[cidx], odate, status, currency, total, addr))
        order_ids.append(cur.fetchone()[0])
    print(f'Inserted {len(order_ids)} orders')

    # Insert order_items
    item_count = 0
    for (oidx, pidx, qty, price, disc) in ORDER_ITEMS:
        cur.execute("""
            INSERT INTO smoke_src.order_items
              (order_id,product_id,quantity,unit_price,discount_pct)
            VALUES (%s,%s,%s,%s,%s)
        """, (order_ids[oidx], prod_ids[pidx], qty, price, disc))
        item_count += 1
    print(f'Inserted {item_count} order_items')

    conn.commit()
    conn.close()

    print()
    print('SOURCE SCHEMA PROVISIONED SUCCESSFULLY.')
    print('Schema: smoke_src  |  Tables: customers, products, orders, order_items')
    print('Total rows:', len(CUSTOMERS) + len(PRODUCTS) + len(ORDERS) + item_count)


if __name__ == '__main__':
    provision()

"""
AKAAL Smoke Migration — Step 1b: Publish smoke_src tables to public schema.

Copies the smoke_src schema tables into public for AKAAL adapter consumption.
The source data is identical — this is equivalent to having the migration source
in the public schema (PostgreSQL default schema).
"""
import psycopg2

PG = dict(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='postgres')

SQL = """
-- Drop old smoke tables in public if present
DROP TABLE IF EXISTS public.order_items CASCADE;
DROP TABLE IF EXISTS public.orders      CASCADE;
DROP TABLE IF EXISTS public.products    CASCADE;
DROP TABLE IF EXISTS public.customers   CASCADE;

-- Clone from smoke_src (full copy including constraints)
CREATE TABLE public.customers   AS SELECT * FROM smoke_src.customers;
CREATE TABLE public.products    AS SELECT * FROM smoke_src.products;
CREATE TABLE public.orders      AS SELECT * FROM smoke_src.orders;
CREATE TABLE public.order_items AS SELECT * FROM smoke_src.order_items;

-- Re-add primary keys
ALTER TABLE public.customers   ADD PRIMARY KEY (customer_id);
ALTER TABLE public.products    ADD PRIMARY KEY (product_id);
ALTER TABLE public.orders      ADD PRIMARY KEY (order_id);
ALTER TABLE public.order_items ADD PRIMARY KEY (item_id);

-- Re-add foreign keys
ALTER TABLE public.orders
    ADD CONSTRAINT fk_orders_customer
    FOREIGN KEY (customer_id) REFERENCES public.customers(customer_id);

ALTER TABLE public.order_items
    ADD CONSTRAINT fk_items_order
    FOREIGN KEY (order_id) REFERENCES public.orders(order_id);

ALTER TABLE public.order_items
    ADD CONSTRAINT fk_items_product
    FOREIGN KEY (product_id) REFERENCES public.products(product_id);

-- Re-add unique constraints
ALTER TABLE public.customers ADD CONSTRAINT uq_customers_email UNIQUE (email);
ALTER TABLE public.products  ADD CONSTRAINT uq_products_sku    UNIQUE (sku);
ALTER TABLE public.order_items ADD CONSTRAINT uq_order_product UNIQUE (order_id, product_id);

-- Re-add check constraints
ALTER TABLE public.products ADD CONSTRAINT chk_price_positive CHECK (unit_price >= 0);
ALTER TABLE public.products ADD CONSTRAINT chk_stock_nonneg   CHECK (stock_qty  >= 0);
ALTER TABLE public.orders   ADD CONSTRAINT chk_order_status   CHECK (status IN ('PENDING','CONFIRMED','SHIPPED','DELIVERED','CANCELLED'));
ALTER TABLE public.order_items ADD CONSTRAINT chk_qty_positive   CHECK (quantity     > 0);
ALTER TABLE public.order_items ADD CONSTRAINT chk_discount_range CHECK (discount_pct BETWEEN 0 AND 100);

-- Re-add indexes
CREATE INDEX idx_customers_email   ON public.customers (email);
CREATE INDEX idx_customers_country ON public.customers (country_code);
CREATE INDEX idx_products_sku      ON public.products  (sku);
CREATE INDEX idx_products_category ON public.products  (category);
CREATE INDEX idx_orders_customer   ON public.orders    (customer_id);
CREATE INDEX idx_orders_date       ON public.orders    (order_date);
CREATE INDEX idx_orders_status     ON public.orders    (status);
CREATE INDEX idx_order_items_order   ON public.order_items (order_id);
CREATE INDEX idx_order_items_product ON public.order_items (product_id);
"""

conn = psycopg2.connect(**PG)
conn.autocommit = False
cur = conn.cursor()
cur.execute(SQL)
conn.commit()

# Verify
tables = ['customers', 'products', 'orders', 'order_items']
print('=== PUBLIC SCHEMA VERIFICATION ===')
total = 0
for t in tables:
    cur.execute(f'SELECT COUNT(*) FROM public.{t}')
    cnt = cur.fetchone()[0]
    total += cnt
    print(f'  public.{t}: {cnt} rows')

print(f'  Total rows: {total}')

# Verify a sample of data
cur.execute("SELECT customer_id, first_name, last_name, email, country_code FROM public.customers ORDER BY customer_id")
rows = cur.fetchall()
print()
print('Sample customers:')
for r in rows[:3]:
    print(f'  {r}')

conn.close()
print()
print('PUBLIC SCHEMA TABLES READY FOR AKAAL MIGRATION')

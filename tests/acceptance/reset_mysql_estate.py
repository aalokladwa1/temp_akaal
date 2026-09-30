import pymysql
import datetime
import glob
import os

def reset_mysql_estate():
    # Clean up prior snapshot files
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "akaalPipeline", "data"))
    for f in glob.glob(os.path.join(data_dir, "cdc_snap_*.json")):
        try:
            os.remove(f)
        except Exception:
            pass

    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='devkros_p8_m2_cdc',
        password='DevKros#P8#Src2026',
        database='devkros_p8_m2',
        autocommit=True
    )
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS ORDER_ITEMS")
    cur.execute("DROP TABLE IF EXISTS ORDERS")
    cur.execute("DROP TABLE IF EXISTS PRODUCTS")
    cur.execute("DROP TABLE IF EXISTS CUSTOMERS")
    cur.execute("DROP TABLE IF EXISTS EMPLOYEES")
    cur.execute("DROP TABLE IF EXISTS DEPARTMENTS")
    cur.execute("DROP TABLE IF EXISTS CDC_TEST_AUDIT")

    cur.execute("""
    CREATE TABLE DEPARTMENTS (
        DEPARTMENT_ID INT PRIMARY KEY,
        DEPARTMENT_NAME VARCHAR(100) NOT NULL,
        LOCATION VARCHAR(100) NOT NULL
    ) ENGINE=InnoDB
    """)

    cur.execute("""
    CREATE TABLE EMPLOYEES (
        EMPLOYEE_ID INT PRIMARY KEY,
        FIRST_NAME VARCHAR(50) NOT NULL,
        LAST_NAME VARCHAR(50) NOT NULL,
        EMAIL VARCHAR(100) NOT NULL UNIQUE,
        TAX_IDENTIFIER VARCHAR(20) NOT NULL UNIQUE,
        HIRE_DATE DATE NOT NULL,
        SALARY DECIMAL(10, 2) NOT NULL,
        DEPARTMENT_ID INT NOT NULL,
        IS_ACTIVE TINYINT(1) DEFAULT 1,
        FOREIGN KEY (DEPARTMENT_ID) REFERENCES DEPARTMENTS(DEPARTMENT_ID)
    ) ENGINE=InnoDB
    """)

    cur.execute("""
    CREATE TABLE CUSTOMERS (
        CUSTOMER_ID INT PRIMARY KEY,
        CUSTOMER_NAME VARCHAR(100) NOT NULL,
        EMAIL VARCHAR(100) NOT NULL UNIQUE,
        PHONE VARCHAR(30),
        SECONDARY_PHONE VARCHAR(30) NULL,
        NOTES MEDIUMTEXT,
        IS_ACTIVE TINYINT(1) DEFAULT 1
    ) ENGINE=InnoDB
    """)

    cur.execute("""
    CREATE TABLE PRODUCTS (
        PRODUCT_ID INT PRIMARY KEY,
        PRODUCT_NAME VARCHAR(100) NOT NULL,
        CATEGORY VARCHAR(50) NOT NULL,
        PRICE DECIMAL(10, 2) NOT NULL,
        STOCK_QTY SMALLINT NOT NULL,
        DESCRIPTION TEXT
    ) ENGINE=InnoDB
    """)

    cur.execute("""
    CREATE TABLE ORDERS (
        ORDER_ID INT PRIMARY KEY,
        CUSTOMER_ID INT NOT NULL,
        EMPLOYEE_ID INT NOT NULL,
        ORDER_DATE DATETIME(6) NOT NULL,
        DELIVERY_DATE DATETIME(6) NULL,
        TOTAL_AMOUNT DECIMAL(12, 2) NOT NULL,
        TRANSACTION_REF BIGINT NOT NULL,
        STATUS VARCHAR(20) NOT NULL,
        FOREIGN KEY (CUSTOMER_ID) REFERENCES CUSTOMERS(CUSTOMER_ID),
        FOREIGN KEY (EMPLOYEE_ID) REFERENCES EMPLOYEES(EMPLOYEE_ID)
    ) ENGINE=InnoDB
    """)

    cur.execute("""
    CREATE TABLE ORDER_ITEMS (
        ORDER_ID INT NOT NULL,
        LINE_NO INT NOT NULL,
        PRODUCT_ID INT NOT NULL,
        QUANTITY INT NOT NULL,
        UNIT_PRICE DECIMAL(12, 2) NOT NULL,
        DISCOUNT_RATE DECIMAL(8, 4) DEFAULT 0.0000,
        PRIMARY KEY (ORDER_ID, LINE_NO),
        FOREIGN KEY (ORDER_ID) REFERENCES ORDERS(ORDER_ID),
        FOREIGN KEY (PRODUCT_ID) REFERENCES PRODUCTS(PRODUCT_ID)
    ) ENGINE=InnoDB
    """)

    cur.execute("""
    CREATE TABLE CDC_TEST_AUDIT (
        AUDIT_EVENT_ID INT PRIMARY KEY,
        EVENT_TYPE VARCHAR(50) NOT NULL,
        RAW_PAYLOAD LONGTEXT,
        CREATED_AT TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6)
    ) ENGINE=InnoDB
    """)

    # Seed DEPARTMENTS (25)
    dept_rows = [(i, f'Department_{i}', f'City_Zone_{i % 5}') for i in range(1, 26)]
    cur.executemany("INSERT INTO DEPARTMENTS VALUES (%s, %s, %s)", dept_rows)

    # Seed EMPLOYEES (800)
    base_date = datetime.date(2020, 1, 1)
    emp_rows = []
    for i in range(1, 801):
        hire = base_date + datetime.timedelta(days=(i % 1500))
        emp_rows.append((
            i, f'EmpFirst_{i}', f'EmpLast_{i}', f'emp_{i}@devkros-corp.com',
            f'TAX-ID-{i:06d}', hire, 35000.0 + (i * 15.5), 1 + (i % 25), 1
        ))
    cur.executemany("INSERT INTO EMPLOYEES VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", emp_rows)

    # Seed CUSTOMERS (1200)
    cust_rows = []
    for i in range(1, 1201):
        if i == 1: name = 'José Silva'
        elif i == 2: name = 'Hans Müller'
        elif i == 3: name = '山田太郎'
        elif i == 4: name = 'अमित शर्मा'
        else: name = f'Customer_{i}'
        sec_phone = f'+1-800-{i:04d}' if (i % 3 == 0) else None
        cust_rows.append((
            i, name, f'client_{i}@customer-domain.org', f'+1-555-{i:04d}',
            sec_phone, f'Notes for customer record {i} with deterministic text padding.', 1
        ))
    cur.executemany("INSERT INTO CUSTOMERS VALUES (%s, %s, %s, %s, %s, %s, %s)", cust_rows)

    # Seed PRODUCTS (350)
    prod_rows = [
        (i, f'Product_SKU_{i}', f'Category_{i % 10}', 10.0 + (i * 2.25), 100 + (i % 50),
         f'Full product description and technical specification payload for SKU item {i}')
        for i in range(1, 351)
    ]
    cur.executemany("INSERT INTO PRODUCTS VALUES (%s, %s, %s, %s, %s, %s)", prod_rows)

    # Seed ORDERS (4500) & ORDER_ITEMS (8125)
    order_base = datetime.datetime(2025, 1, 1, 8, 0, 0)
    ord_rows = []
    item_rows = []
    for i in range(1, 4501):
        ord_date = order_base + datetime.timedelta(minutes=(i * 2))
        del_date = (order_base + datetime.timedelta(hours=(i * 2 + 72))) if (i % 4 == 0) else None
        status = 'CANCELLED' if (i % 10 == 0) else 'COMPLETED'
        ord_rows.append((
            i, 1 + (i % 1200), 1 + (i % 800), ord_date, del_date,
            150.0 + (i % 500), 1000000000 + i, status
        ))
        item_rows.append((i, 1, 1 + (i % 350), 1, 25.50, 0.0500))
        if i <= 3625:
            item_rows.append((i, 2, 1 + ((i + 7) % 350), 2, 45.00, 0.0000))

    for batch in [ord_rows[i:i + 1000] for i in range(0, len(ord_rows), 1000)]:
        cur.executemany("INSERT INTO ORDERS VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", batch)
    for batch in [item_rows[i:i + 1000] for i in range(0, len(item_rows), 1000)]:
        cur.executemany("INSERT INTO ORDER_ITEMS VALUES (%s, %s, %s, %s, %s, %s)", batch)

    # Seed CDC_TEST_AUDIT (50)
    audit_rows = [
        (i, f'SYSTEM_EVENT_{i % 5}', f'{{"event_id":{i},"status":"INITIAL_SEEDED_STATE"}}')
        for i in range(1, 51)
    ]
    cur.executemany("INSERT INTO CDC_TEST_AUDIT (AUDIT_EVENT_ID, EVENT_TYPE, RAW_PAYLOAD) VALUES (%s, %s, %s)", audit_rows)

    conn.close()
    print("MySQL devkros_p8_m2 source reset and seeded to 15,050 rows.")

if __name__ == '__main__':
    reset_mysql_estate()

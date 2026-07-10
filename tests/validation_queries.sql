-- validation_queries.sql
-- Refined Enterprise Validation Queries (MySQL Source vs PostgreSQL Target)
-- Compatibility: MySQL 8.0+ and PostgreSQL 16+

-- ============================================================================
-- PART 1: SCHEMA STRUCTURAL VALIDATION (MYSQL vs POSTGRESQL)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1.1 TABLE COUNT
-- ----------------------------------------------------------------------------
-- [MySQL Source]
SELECT COUNT(*) AS table_count 
FROM information_schema.tables 
WHERE table_schema = 'akaal_validation' AND table_type = 'BASE TABLE';

-- [PostgreSQL Target]
SELECT COUNT(*) AS table_count 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';


-- ----------------------------------------------------------------------------
-- 1.2 COLUMN COUNT, COLUMN ORDER & DATA TYPE COMPARISON
-- ----------------------------------------------------------------------------
-- [MySQL Source]
SELECT TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM information_schema.columns
WHERE table_schema = 'akaal_validation'
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- [PostgreSQL Target]
SELECT table_name, column_name, ordinal_position, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;


-- ----------------------------------------------------------------------------
-- 1.3 PRIMARY KEY DEFINITION Check
-- ----------------------------------------------------------------------------
-- [MySQL Source]
SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME
FROM information_schema.key_column_usage
WHERE table_schema = 'akaal_validation' AND constraint_name = 'PRIMARY'
ORDER BY TABLE_NAME;

-- [PostgreSQL Target]
SELECT kcu.table_name, kcu.column_name, tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
WHERE tc.table_schema = 'public' AND tc.constraint_type = 'PRIMARY KEY'
ORDER BY kcu.table_name;


-- ----------------------------------------------------------------------------
-- 1.4 FOREIGN KEY DEFINITION Check
-- ----------------------------------------------------------------------------
-- [MySQL Source]
SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM information_schema.key_column_usage
WHERE table_schema = 'akaal_validation' AND referenced_table_name IS NOT NULL
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

-- [PostgreSQL Target]
SELECT 
    tc.table_name AS local_table,
    kcu.column_name AS local_column,
    tc.constraint_name,
    ccu.table_name AS foreign_table,
    ccu.column_name AS foreign_column
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_name;


-- ----------------------------------------------------------------------------
-- 1.5 UNIQUE & INDEX COUNT
-- ----------------------------------------------------------------------------
-- [MySQL Source]
-- Unique Constraints count
SELECT COUNT(*) AS unique_constraint_count
FROM information_schema.table_constraints
WHERE table_schema = 'akaal_validation' AND constraint_type = 'UNIQUE';

-- Total Index Count (including Primary Keys)
SELECT COUNT(DISTINCT INDEX_NAME) AS index_count
FROM information_schema.statistics
WHERE table_schema = 'akaal_validation';

-- Detailed index metadata
SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, COLUMN_NAME, SEQ_IN_INDEX
FROM information_schema.statistics
WHERE table_schema = 'akaal_validation'
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

-- [PostgreSQL Target]
-- Unique Constraints count
SELECT COUNT(*) AS unique_constraint_count
FROM information_schema.table_constraints
WHERE table_schema = 'public' AND constraint_type = 'UNIQUE';

-- Total Index Count (including Primary Keys)
SELECT COUNT(*) AS index_count
FROM pg_indexes
WHERE schemaname = 'public';

-- Detailed index metadata
SELECT tablename AS table_name, indexname AS index_name, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;


-- ============================================================================
-- PART 2: DATA CONTENT INTEGRITY VALIDATION
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 2.1 ROW COUNTS & MIN/MAX PRIMARY KEY IDs
-- ----------------------------------------------------------------------------
-- [MySQL Source & PostgreSQL Target]
SELECT 'users' AS tbl, COUNT(*) AS count, MIN(id) AS min_id, MAX(id) AS max_id FROM users
UNION ALL SELECT 'products', COUNT(*), MIN(id), MAX(id) FROM products
UNION ALL SELECT 'orders', COUNT(*), MIN(id), MAX(id) FROM orders
UNION ALL SELECT 'order_items', COUNT(*), MIN(id), MAX(id) FROM order_items
UNION ALL SELECT 'audit_logs', COUNT(*), MIN(id), MAX(id) FROM audit_logs;


-- ----------------------------------------------------------------------------
-- 2.2 DUPLICATE PRIMARY KEYS DETECTION (Should return 0 rows)
-- ----------------------------------------------------------------------------
-- [MySQL Source & PostgreSQL Target]
SELECT id, COUNT(*) AS dup_count FROM users GROUP BY id HAVING COUNT(*) > 1;
SELECT id, COUNT(*) AS dup_count FROM products GROUP BY id HAVING COUNT(*) > 1;
SELECT id, COUNT(*) AS dup_count FROM orders GROUP BY id HAVING COUNT(*) > 1;
SELECT id, COUNT(*) AS dup_count FROM order_items GROUP BY id HAVING COUNT(*) > 1;
SELECT id, COUNT(*) AS dup_count FROM audit_logs GROUP BY id HAVING COUNT(*) > 1;


-- ----------------------------------------------------------------------------
-- 2.3 REFERENTIAL INTEGRITY (Orphaned Foreign Keys) - Should return 0 rows
-- ----------------------------------------------------------------------------
-- [MySQL Source & PostgreSQL Target]
-- 1. Orders pointing to non-existent users
SELECT COUNT(*) AS orphaned_orders_user FROM orders o 
LEFT JOIN users u ON o.user_id = u.id 
WHERE u.id IS NULL;

-- 2. Order items pointing to non-existent orders
SELECT COUNT(*) AS orphaned_items_order FROM order_items oi 
LEFT JOIN orders o ON oi.order_id = o.id 
WHERE o.id IS NULL;

-- 3. Order items pointing to non-existent products
SELECT COUNT(*) AS orphaned_items_product FROM order_items oi 
LEFT JOIN products p ON oi.product_id = p.id 
WHERE p.id IS NULL;


-- ----------------------------------------------------------------------------
-- 2.4 DECIMAL AGGREGATE PARITY (Precision and scale verification)
-- ----------------------------------------------------------------------------
-- [MySQL Source & PostgreSQL Target]
SELECT 
    SUM(total_amount) AS sum_total_amount,
    AVG(total_amount) AS avg_total_amount,
    MIN(total_amount) AS min_total_amount,
    MAX(total_amount) AS max_total_amount
FROM orders;


-- ----------------------------------------------------------------------------
-- 2.5 TIMESTAMP PRECISION AND LIMITS
-- ----------------------------------------------------------------------------
-- [MySQL Source & PostgreSQL Target]
SELECT 
    MIN(created_at) AS earliest_user_created, 
    MAX(created_at) AS latest_user_created,
    MIN(order_date) AS earliest_order_date, 
    MAX(order_date) AS latest_order_date,
    MIN(logged_at) AS earliest_audit_log,
    MAX(logged_at) AS latest_audit_log
FROM orders o
JOIN users u ON o.user_id = u.id
JOIN audit_logs al ON al.entity_id = o.id;


-- ----------------------------------------------------------------------------
-- 2.6 NULL vs EMPTY STRING COUNTS (Validates exact cell matching)
-- ----------------------------------------------------------------------------
-- [MySQL Source & PostgreSQL Target]
SELECT 
    COUNT(*) AS total_rows,
    SUM(CASE WHEN description IS NULL THEN 1 ELSE 0 END) AS desc_null_count,
    SUM(CASE WHEN description = '' THEN 1 ELSE 0 END) AS desc_empty_count,
    SUM(CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) AS desc_populated_count
FROM products;

SELECT 
    COUNT(*) AS total_orders,
    SUM(CASE WHEN shipping_address IS NULL THEN 1 ELSE 0 END) AS addr_null_count,
    SUM(CASE WHEN shipping_address = '' THEN 1 ELSE 0 END) AS addr_empty_count
FROM orders;


-- ----------------------------------------------------------------------------
-- 2.7 JSON INTEGRITY (Validity, key extraction, length check)
-- ----------------------------------------------------------------------------
-- [MySQL Source]
SELECT 
    COUNT(*) AS json_rows,
    SUM(CASE WHEN JSON_VALID(attributes) THEN 1 ELSE 0 END) AS valid_json_count,
    JSON_UNQUOTE(JSON_EXTRACT(attributes, '$.category')) AS extracted_category,
    LENGTH(JSON_EXTRACT(attributes, '$.details')) AS details_length
FROM products 
WHERE attributes IS NOT NULL
GROUP BY extracted_category, details_length
LIMIT 5;

-- [PostgreSQL Target]
SELECT 
    COUNT(*) AS json_rows,
    COUNT(attributes) AS valid_json_count,  -- Target PostgreSQL column validation is checked implicitly
    attributes->>'category' AS extracted_category,
    length(attributes->'details') AS details_length
FROM products 
WHERE attributes IS NOT NULL
GROUP BY extracted_category, details_length
LIMIT 5;


-- ----------------------------------------------------------------------------
-- 2.8 BLOB INTEGRITY & HASH VERIFICATION (SHA256 with MD5 fallback)
-- ----------------------------------------------------------------------------
-- [MySQL Source]
SELECT 
    SUM(LENGTH(raw_payload)) AS total_blob_bytes,
    AVG(LENGTH(raw_payload)) AS avg_blob_bytes,
    SHA2(raw_payload, 256) AS payload_hash
FROM audit_logs 
WHERE id = 50000
GROUP BY raw_payload;

-- [PostgreSQL Target]
-- Define helper function if not exists to check extension dynamically without parser crashes
CREATE OR REPLACE FUNCTION portable_sha256(payload bytea) 
RETURNS text AS $$
DECLARE
    result text;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
        EXECUTE 'SELECT encode(digest($1, ''sha256''), ''hex'')' INTO result USING payload;
    ELSE
        result := md5(payload); -- Graceful fallback to native MD5 hex string representation
    END IF;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

SELECT 
    SUM(octet_length(raw_payload)) AS total_blob_bytes,
    AVG(octet_length(raw_payload)) AS avg_blob_bytes,
    portable_sha256(raw_payload) AS payload_hash
FROM audit_logs 
WHERE id = 50000
GROUP BY raw_payload;


-- ----------------------------------------------------------------------------
-- 2.9 AUTO INCREMENT / CURRENT SEQUENCE VALUES
-- ----------------------------------------------------------------------------
-- [MySQL Source]
SELECT TABLE_NAME, AUTO_INCREMENT
FROM information_schema.tables
WHERE table_schema = 'akaal_validation' AND AUTO_INCREMENT IS NOT NULL;

-- [PostgreSQL Target]
SELECT 
    c.relname AS sequence_name,
    pg_sequence_last_value(c.oid) AS last_sequence_value
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'S' AND n.nspname = 'public';

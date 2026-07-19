-- sample_schema.sql
-- Enterprise Validation Schema for Akaal: MySQL Source Database
-- Name: akaal_validation

CREATE DATABASE IF NOT EXISTS akaal_validation;
USE akaal_validation;

-- 1. Drop existing tables if they exist (in dependency order)
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- 2. Create tables

-- Users Table: Exercises Auto-increment, VARCHAR, BOOLEAN/TINYINT, TIMESTAMP, Defaults
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    is_active TINYINT(1) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    INDEX idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Products Table: Exercises TEXT, LONGTEXT, DECIMAL, JSON, UNIQUE index
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    extra_description LONGTEXT,
    attributes JSON,
    is_discounted BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    INDEX idx_products_sku (sku),
    INDEX idx_products_price (price)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Orders Table: Exercises Foreign Key, DATETIME, DECIMAL, FLOAT, DOUBLE, Nullable fields
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    order_date DATETIME NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    tax_amount FLOAT DEFAULT 0.0,
    discount_amount DOUBLE DEFAULT 0.0,
    shipping_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY fk_orders_user (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_orders_user (user_id),
    INDEX idx_orders_date (order_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Order Items Table: Exercises Composite Unique Keys, multiple Foreign Keys
CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY fk_items_order (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY fk_items_product (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY uq_order_product (order_id, product_id),
    INDEX idx_items_order (order_id),
    INDEX idx_items_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Audit Logs Table: Exercises JSON, BLOB / LONGBLOB, CHAR
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_name VARCHAR(100) NOT NULL,
    entity_id INT NOT NULL,
    action_type CHAR(10) NOT NULL,
    old_value JSON,
    new_value JSON,
    raw_payload LONGBLOB,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    INDEX idx_audit_entity (entity_name, entity_id),
    INDEX idx_audit_logged (logged_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- [POSTGRES_START]
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(255), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE products (id SERIAL PRIMARY KEY, name VARCHAR(255), price DECIMAL(10,2));
CREATE TABLE orders (id SERIAL PRIMARY KEY, user_id INT, status VARCHAR(50));
CREATE TABLE order_items (id SERIAL PRIMARY KEY, order_id INT, product_id INT, quantity INT);
CREATE TABLE audit_logs (id SERIAL PRIMARY KEY, entity_name VARCHAR(255), action VARCHAR(255));
-- [POSTGRES_END]

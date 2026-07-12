-- ============================================================
-- MySQL 8.0 - 电商数据仓库建表脚本
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS ecommerce_dw
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE ecommerce_dw;

-- ============================================================
-- ODS层 - 原始数据层
-- ============================================================
DROP TABLE IF EXISTS ods_retail_raw;
CREATE TABLE ods_retail_raw (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    invoiceno VARCHAR(50),
    stockcode VARCHAR(50),
    description TEXT,
    quantity INT,
    invoicedate DATETIME,
    unitprice DECIMAL(10, 2),
    customerid DECIMAL(10, 0),
    country VARCHAR(100),
    etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- DWD层 - 数据明细层
-- ============================================================
DROP TABLE IF EXISTS dwd_order_detail;
CREATE TABLE dwd_order_detail (
    order_detail_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    invoice_no VARCHAR(50),
    stock_code VARCHAR(50),
    description TEXT,
    quantity INT,
    invoice_date DATETIME,
    unit_price DECIMAL(10, 2),
    total_amount DECIMAL(12, 2),
    customer_id DECIMAL(10, 0),
    country VARCHAR(100),
    year INT,
    month INT,
    day INT,
    weekday VARCHAR(10),
    etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- DWS层 - 数据汇总层
-- ============================================================

-- 用户维度表
DROP TABLE IF EXISTS dim_users;
CREATE TABLE dim_users (
    user_sk BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id DECIMAL(10, 0),
    country VARCHAR(100),
    first_purchase_date DATETIME,
    last_purchase_date DATETIME,
    total_orders INT,
    total_amount DECIMAL(12, 2),
    is_active BOOLEAN DEFAULT TRUE,
    etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 商品维度表
DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products (
    product_sk BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(50),
    description TEXT,
    first_sale_date DATETIME,
    last_sale_date DATETIME,
    total_quantity INT,
    total_revenue DECIMAL(12, 2),
    avg_unit_price DECIMAL(10, 2),
    etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 日期维度表
DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date (
    date_sk INT PRIMARY KEY,
    full_date DATE,
    year INT,
    quarter INT,
    month INT,
    day INT,
    weekday VARCHAR(10),
    is_weekend BOOLEAN
) ENGINE=InnoDB;

-- 发票维度表
DROP TABLE IF EXISTS dim_invoice;
CREATE TABLE dim_invoice (
    invoice_sk BIGINT AUTO_INCREMENT PRIMARY KEY,
    invoice_no VARCHAR(50),
    customer_id DECIMAL(10, 0),
    invoice_date DATETIME,
    country VARCHAR(100),
    total_amount DECIMAL(12, 2),
    item_count INT,
    etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 销售事实表
DROP TABLE IF EXISTS fact_sales;
CREATE TABLE fact_sales (
    sales_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_detail_id BIGINT,
    invoice_no VARCHAR(50),
    stock_code VARCHAR(50),
    description TEXT,
    quantity INT,
    unit_price DECIMAL(10, 2),
    total_amount DECIMAL(12, 2),
    customer_id DECIMAL(10, 0),
    country VARCHAR(100),
    invoice_date DATETIME,
    year INT,
    month INT,
    day INT,
    etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- 创建索引以提高查询性能
-- ============================================================
CREATE INDEX idx_ods_invoiceno ON ods_retail_raw(invoiceno);
CREATE INDEX idx_ods_customerid ON ods_retail_raw(customerid);
CREATE INDEX idx_ods_invoicedate ON ods_retail_raw(invoicedate);

CREATE INDEX idx_dwd_invoice_no ON dwd_order_detail(invoice_no);
CREATE INDEX idx_dwd_customer_id ON dwd_order_detail(customer_id);
CREATE INDEX idx_dwd_invoice_date ON dwd_order_detail(invoice_date);
CREATE INDEX idx_dwd_year_month ON dwd_order_detail(year, month);

CREATE INDEX idx_dim_users_customer_id ON dim_users(customer_id);
CREATE INDEX idx_dim_products_stock_code ON dim_products(stock_code);
CREATE INDEX idx_dim_date_full_date ON dim_date(full_date);
CREATE INDEX idx_dim_invoice_invoice_no ON dim_invoice(invoice_no);

CREATE INDEX idx_fact_sales_invoice_no ON fact_sales(invoice_no);
CREATE INDEX idx_fact_sales_customer_id ON fact_sales(customer_id);
CREATE INDEX idx_fact_sales_invoice_date ON fact_sales(invoice_date);
CREATE INDEX idx_fact_sales_year_month ON fact_sales(year, month);
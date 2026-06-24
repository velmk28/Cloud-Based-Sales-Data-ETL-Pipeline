-- Production Star Schema for Cloud-Based Sales ETL Project
-- Database: sales_data

CREATE DATABASE IF NOT EXISTS sales_data;
USE sales_data;

-- -----------------------------------------------------
-- Table: dim_customers
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_customers (
    customer_key INT AUTO_INCREMENT PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    country VARCHAR(100) DEFAULT 'Unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_customer_id (customer_id),
    INDEX idx_customer_country (country)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: dim_products
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_products (
    product_key INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) DEFAULT 'General',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_product_id (product_id),
    INDEX idx_product_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: fact_sales
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    customer_key INT NOT NULL,
    product_key INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    revenue DECIMAL(12, 2) NOT NULL,
    cost DECIMAL(12, 2) NOT NULL,
    profit DECIMAL(12, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_transaction_id (transaction_id),
    CONSTRAINT fk_sales_customer FOREIGN KEY (customer_key) 
        REFERENCES dim_customers(customer_key) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_sales_product FOREIGN KEY (product_key) 
        REFERENCES dim_products(product_key) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_sales_date (date),
    INDEX idx_sales_customer_key (customer_key),
    INDEX idx_sales_product_key (product_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: agg_monthly_sales
-- -----------------------------------------------------
-- Pre-aggregated table for fast business intelligence dashboards
CREATE TABLE IF NOT EXISTS agg_monthly_sales (
    year INT NOT NULL,
    month INT NOT NULL,
    category VARCHAR(100) NOT NULL,
    total_quantity INT NOT NULL,
    total_revenue DECIMAL(15, 2) NOT NULL,
    total_cost DECIMAL(15, 2) NOT NULL,
    total_profit DECIMAL(15, 2) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (year, month, category),
    INDEX idx_agg_year_month (year, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

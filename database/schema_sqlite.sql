-- SQLite Star Schema for local fallback testing
-- Database: sales_data.db

-- -----------------------------------------------------
-- Table: dim_customers
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_customers (
    customer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    country TEXT DEFAULT 'Unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id)
);

-- -----------------------------------------------------
-- Table: dim_products
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_products (
    product_key INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT DEFAULT 'General',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id)
);

-- -----------------------------------------------------
-- Table: fact_sales
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    date DATE NOT NULL,
    customer_key INTEGER NOT NULL,
    product_key INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    revenue REAL NOT NULL,
    cost REAL NOT NULL,
    profit REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(transaction_id),
    FOREIGN KEY (customer_key) REFERENCES dim_customers(customer_key) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (product_key) REFERENCES dim_products(product_key) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- -----------------------------------------------------
-- Table: agg_monthly_sales
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS agg_monthly_sales (
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    category TEXT NOT NULL,
    total_quantity INTEGER NOT NULL,
    total_revenue REAL NOT NULL,
    total_cost REAL NOT NULL,
    total_profit REAL NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (year, month, category)
);

-- -----------------------------------------------------
-- Indexes
-- -----------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_sales_date ON fact_sales(date);
CREATE INDEX IF NOT EXISTS idx_sales_customer_key ON fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS idx_sales_product_key ON fact_sales(product_key);
CREATE INDEX IF NOT EXISTS idx_product_category ON dim_products(category);
CREATE INDEX IF NOT EXISTS idx_customer_country ON dim_customers(country);

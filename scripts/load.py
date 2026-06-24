import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def get_db_connection_uri():
    """Builds database connection URI from environment variables."""
    db_type = os.getenv("DB_TYPE", "mysql").lower()
    if db_type == "sqlite":
        # Save local SQLite file in data folder
        return "sqlite:///data/processed/sales_data.db"
        
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "sales_user")
    password = os.getenv("DB_PASSWORD", "sales_secure_password")
    db_name = os.getenv("DB_NAME", "sales_data")
    
    # Use PyMySQL driver for MySQL connection
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"

def get_db_engine():
    """Creates and returns SQLAlchemy engine."""
    connection_uri = get_db_connection_uri()
    try:
        engine = create_engine(
            connection_uri, 
            pool_recycle=3600, 
            pool_size=10, 
            max_overflow=20
        )
        return engine
    except Exception as e:
        logger.error(f"Failed to create SQLAlchemy engine: {e}")
        raise

def init_db(schema_path, engine):
    """
    Initializes the database schema by executing statements in schema.sql.
    Ensures tables, constraints, and indexes exist before loading data.
    """
    logger.info(f"Initializing database schema from {schema_path}...")
    if not os.path.exists(schema_path):
        logger.error(f"Schema file not found at: {schema_path}")
        return False
        
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            
        # Split sql queries by semicolon (simple sql parser)
        statements = schema_sql.split(";")
        
        with engine.begin() as conn:
            for statement in statements:
                stmt_stripped = statement.strip()
                if stmt_stripped:
                    conn.execute(text(stmt_stripped))
                    
        logger.info("Database schema initialized successfully.")
        return True
    except (SQLAlchemyError, Exception) as e:
        logger.error(f"Error during schema initialization: {e}")
        return False

def load_dimensions(df, engine):
    """
    Extracts unique dimensions from the dataframe and loads them into:
    - dim_customers (unique Customer_ID)
    - dim_products (unique Product_ID)
    Implements a safe 'Upsert' strategy using pandas-based delta checks.
    """
    try:
        with engine.begin() as conn:
            # 1. Load Customers
            logger.info("Loading dim_customers...")
            raw_customers = df[["Customer_ID", "Country"]].dropna(subset=["Customer_ID"])
            # Remove local duplicates in dataset
            raw_customers = raw_customers.drop_duplicates(subset=["Customer_ID"])
            
            # Fetch existing customers from DB
            existing_cust_df = pd.read_sql("SELECT customer_id FROM dim_customers", conn)
            existing_custs = set(existing_cust_df["customer_id"].tolist())
            
            # Filter only new customers
            new_customers = raw_customers[~raw_customers["Customer_ID"].isin(existing_custs)]
            if not new_customers.empty:
                new_customers = new_customers.rename(columns={
                    "Customer_ID": "customer_id",
                    "Country": "country"
                })
                new_customers.to_sql(
                    "dim_customers", 
                    con=conn, 
                    if_exists="append", 
                    index=False
                )
                logger.info(f" -> Inserted {len(new_customers)} new customers into dim_customers.")
            else:
                logger.info(" -> No new customers to insert.")
                
            # 2. Load Products
            logger.info("Loading dim_products...")
            raw_products = df[["Product_ID", "Product_Name", "Category"]].dropna(subset=["Product_ID"])
            raw_products = raw_products.drop_duplicates(subset=["Product_ID"])
            
            # Fetch existing products from DB
            existing_prod_df = pd.read_sql("SELECT product_id FROM dim_products", conn)
            existing_prods = set(existing_prod_df["product_id"].tolist())
            
            # Filter only new products
            new_products = raw_products[~raw_products["Product_ID"].isin(existing_prods)]
            if not new_products.empty:
                new_products = new_products.rename(columns={
                    "Product_ID": "product_id",
                    "Product_Name": "product_name",
                    "Category": "category"
                })
                new_products.to_sql(
                    "dim_products", 
                    con=conn, 
                    if_exists="append", 
                    index=False
                )
                logger.info(f" -> Inserted {len(new_products)} new products into dim_products.")
            else:
                logger.info(" -> No new products to insert.")
                
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error loading dimensions: {e}")
        return False

def load_facts(df, engine):
    """
    Joins the cleaned dataset with dimension tables to retrieve surrogate keys
    (customer_key, product_key) and loads the records into fact_sales.
    """
    logger.info("Loading fact_sales...")
    try:
        with engine.begin() as conn:
            # 1. Fetch current dimensions to map natural keys -> surrogate keys
            cust_dim = pd.read_sql("SELECT customer_key, customer_id FROM dim_customers", conn)
            prod_dim = pd.read_sql("SELECT product_key, product_id FROM dim_products", conn)
            
            # 2. Map dimensions
            mapped_df = df.merge(cust_dim, left_on="Customer_ID", right_on="customer_id", how="inner")
            mapped_df = mapped_df.merge(prod_dim, left_on="Product_ID", right_on="product_id", how="inner")
            
            # 3. Fetch existing transaction IDs to prevent duplicate facts
            existing_tx_df = pd.read_sql("SELECT transaction_id FROM fact_sales", conn)
            existing_txs = set(existing_tx_df["transaction_id"].tolist())
            
            # Filter new records only
            new_sales = mapped_df[~mapped_df["Transaction_ID"].isin(existing_txs)]
            
            if new_sales.empty:
                logger.info(" -> No new transactions to load into fact_sales.")
                return True
                
            # 4. Prepare fact schema
            fact_df = new_sales[[
                "Transaction_ID", "Date", "customer_key", "product_key",
                "Quantity", "Unit_Price", "Revenue", "Cost", "Profit"
            ]].rename(columns={
                "Transaction_ID": "transaction_id",
                "Date": "date",
                "Quantity": "quantity",
                "Unit_Price": "unit_price",
                "Revenue": "revenue",
                "Cost": "cost",
                "Profit": "profit"
            })
            
            # 5. Bulk insert to fact_sales
            fact_df.to_sql(
                "fact_sales",
                con=conn,
                if_exists="append",
                index=False
            )
            logger.info(f" -> Bulk loaded {len(fact_df)} records into fact_sales.")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Error loading fact tables: {e}")
        return False

def load_monthly_aggregates(monthly_df, engine):
    """
    Loads aggregated monthly statistics. 
    Uses 'ON DUPLICATE KEY UPDATE' (MySQL) or 'ON CONFLICT' (SQLite) to refresh monthly aggregates.
    """
    logger.info("Loading agg_monthly_sales...")
    if monthly_df.empty:
        logger.info(" -> No monthly sales summary data to load.")
        return True
        
    try:
        # Determine database dialect
        if "sqlite" in engine.name:
            upsert_query = text("""
                INSERT INTO agg_monthly_sales (
                    year, month, category, total_quantity, total_revenue, total_cost, total_profit
                ) VALUES (
                    :year, :month, :category, :total_quantity, :total_revenue, :total_cost, :total_profit
                ) ON CONFLICT(year, month, category) DO UPDATE SET
                    total_quantity = excluded.total_quantity,
                    total_revenue = excluded.total_revenue,
                    total_cost = excluded.total_cost,
                    total_profit = excluded.total_profit;
            """)
        else:
            # SQL upsert template for MySQL
            upsert_query = text("""
                INSERT INTO agg_monthly_sales (
                    year, month, category, total_quantity, total_revenue, total_cost, total_profit
                ) VALUES (
                    :year, :month, :category, :total_quantity, :total_revenue, :total_cost, :total_profit
                ) ON DUPLICATE KEY UPDATE
                    total_quantity = VALUES(total_quantity),
                    total_revenue = VALUES(total_revenue),
                    total_cost = VALUES(total_cost),
                    total_profit = VALUES(total_profit);
            """)
        
        records = monthly_df.to_dict(orient="records")
        
        with engine.begin() as conn:
            for rec in records:
                conn.execute(upsert_query, {
                    "year": int(rec["Year"]),
                    "month": int(rec["Month"]),
                    "category": str(rec["Category"]),
                    "total_quantity": int(rec["total_quantity"]),
                    "total_revenue": float(rec["total_revenue"]),
                    "total_cost": float(rec["total_cost"]),
                    "total_profit": float(rec["total_profit"])
                })
                
        logger.info(f" -> Refreshed {len(records)} category-month sales aggregate cells.")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error loading monthly aggregates: {e}")
        return False

def run_load_pipeline(transformed_df, monthly_df, schema_path):
    """Orchestrates DB connection, schema creation, dimension load, and fact load."""
    logger.info("Starting Load Phase...")
    try:
        engine = get_db_engine()
        
        # Override schema path if using SQLite database
        if "sqlite" in engine.name:
            schema_path = os.path.join("database", "schema_sqlite.sql")
            
        # 1. Initialize schema
        schema_success = init_db(schema_path, engine)
        if not schema_success:
            logger.error("DB Initialization failed. Aborting Load Phase.")
            return False
            
        # 2. Load Dimensions
        dim_success = load_dimensions(transformed_df, engine)
        if not dim_success:
            logger.error("Dimension Loading failed. Aborting Load Phase.")
            return False
            
        # 3. Load Facts
        fact_success = load_facts(transformed_df, engine)
        if not fact_success:
            logger.error("Fact Loading failed. Aborting Load Phase.")
            return False
            
        # 4. Load Monthly aggregates
        agg_success = load_monthly_aggregates(monthly_df, engine)
        if not agg_success:
            logger.error("Monthly aggregate loading failed.")
            return False
            
        logger.info("Load Phase completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to execute Load Pipeline: {e}")
        return False

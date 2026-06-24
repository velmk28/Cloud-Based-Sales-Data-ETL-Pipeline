import os
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Category margin definitions to calculate Cost and Profit dynamically
CATEGORY_MARGINS = {
    "electronics": 0.25,      # 25% profit margin
    "furniture": 0.35,        # 35% profit margin
    "home & kitchen": 0.40,   # 40% profit margin
    "apparel": 0.50,          # 50% profit margin
    "general": 0.30           # Default 30% margin
}

def clean_data(df):
    """
    Cleans raw DataFrame:
    - Removes exact duplicates.
    - Resolves nulls in critical identifiers.
    - Imputes non-critical nulls.
    - Standardizes date formats.
    - Ensures numeric columns are correct and positive.
    Returns: Cleaned DataFrame, Dict of cleaning statistics.
    """
    stats = {
        "raw_records": len(df),
        "duplicates_removed": 0,
        "null_transactions_dropped": 0,
        "invalid_numeric_dropped": 0,
        "dates_standardized": 0,
        "imputed_countries": 0,
        "imputed_categories": 0
    }
    
    if df.empty:
        logger.warning("Empty DataFrame passed to transformation module.")
        return df, stats
        
    # Copy DataFrame to avoid modifying original
    cleaned_df = df.copy()
    
    # 1. Deduplication
    initial_len = len(cleaned_df)
    cleaned_df.drop_duplicates(subset=["Transaction_ID"], keep="first", inplace=True)
    stats["duplicates_removed"] = int(initial_len - len(cleaned_df))
    if stats["duplicates_removed"] > 0:
        logger.info(f"Deduplication: Removed {stats['duplicates_removed']} duplicate records.")
        
    # 2. Critical Fields validation: Drop records without Transaction ID, Product ID, or Date
    critical_cols = ["Transaction_ID", "Product_ID", "Date"]
    before_drop = len(cleaned_df)
    
    # Drop rows where critical columns are null or empty whitespace
    for col in critical_cols:
        cleaned_df = cleaned_df[cleaned_df[col].notna()]
        cleaned_df = cleaned_df[cleaned_df[col].astype(str).str.strip() != ""]
        
    stats["null_transactions_dropped"] = int(before_drop - len(cleaned_df))
    if stats["null_transactions_dropped"] > 0:
        logger.warning(f"Data Quality: Dropped {stats['null_transactions_dropped']} rows due to missing critical IDs.")
        
    # 3. Date Standardization
    # Converts strings of various formats into standardized YYYY-MM-DD
    parsed_dates = []
    failed_dates_indices = []
    
    # Supported input formats for parsing
    date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"]
    
    for idx, row in cleaned_df.iterrows():
        date_str = str(row["Date"]).strip()
        parsed_dt = None
        for fmt in date_formats:
            try:
                parsed_dt = datetime_val = pd.to_datetime(date_str, format=fmt, errors="raise")
                break
            except (ValueError, TypeError):
                continue
                
        if parsed_dt is None:
            # Fallback to pandas generic parser
            try:
                parsed_dt = pd.to_datetime(date_str, errors="raise")
            except Exception:
                pass
                
        if parsed_dt is not None:
            parsed_dates.append(parsed_dt.date())
            stats["dates_standardized"] += 1
        else:
            parsed_dates.append(None)
            failed_dates_indices.append(idx)
            
    cleaned_df["Date"] = parsed_dates
    
    # Drop dates that could not be parsed
    if failed_dates_indices:
        logger.warning(f"Data Quality: Dropped {len(failed_dates_indices)} rows due to unparsable dates.")
        cleaned_df.drop(index=failed_dates_indices, inplace=True)
        stats["null_transactions_dropped"] += len(failed_dates_indices)
        
    # 4. Standardize Text Casing and Impute Missing Strings
    # Category: convert to lower for matching, standardize title case
    cleaned_df["Category"] = cleaned_df["Category"].fillna("General").astype(str).str.strip().str.lower()
    stats["imputed_categories"] = int((cleaned_df["Category"] == "general").sum())
    cleaned_df["Category"] = cleaned_df["Category"].replace("", "general")
    # Clean text to Standard Title Case
    cleaned_df["Category"] = cleaned_df["Category"].apply(lambda x: "Home & Kitchen" if x in ["home & kitchen", "home and kitchen"] else x.title())
    
    # Product Name
    cleaned_df["Product_Name"] = cleaned_df["Product_Name"].fillna("Unknown Product").astype(str).str.strip()
    cleaned_df.loc[cleaned_df["Product_Name"] == "", "Product_Name"] = "Unknown Product"
    
    # Customer ID
    cleaned_df["Customer_ID"] = cleaned_df["Customer_ID"].fillna("GUEST").astype(str).str.strip()
    cleaned_df.loc[cleaned_df["Customer_ID"] == "", "Customer_ID"] = "GUEST"
    
    # Country
    country_nulls = cleaned_df["Country"].isna() | (cleaned_df["Country"].astype(str).str.strip() == "")
    stats["imputed_countries"] = int(country_nulls.sum())
    cleaned_df["Country"] = cleaned_df["Country"].fillna("Unknown").astype(str).str.strip()
    cleaned_df.loc[cleaned_df["Country"] == "", "Country"] = "Unknown"
    
    # 5. Numeric Columns Validation
    # Cast quantity and unit price to numeric. Replace non-numeric with NaN, then filter out.
    cleaned_df["Quantity"] = pd.to_numeric(cleaned_df["Quantity"], errors="coerce")
    cleaned_df["Unit_Price"] = pd.to_numeric(cleaned_df["Unit_Price"], errors="coerce")
    
    before_num_drop = len(cleaned_df)
    # Filter for positive quantities and prices
    cleaned_df = cleaned_df[(cleaned_df["Quantity"] > 0) & (cleaned_df["Unit_Price"] > 0)]
    cleaned_df["Quantity"] = cleaned_df["Quantity"].astype(int)
    cleaned_df["Unit_Price"] = cleaned_df["Unit_Price"].astype(float)
    
    stats["invalid_numeric_dropped"] = int(before_num_drop - len(cleaned_df))
    if stats["invalid_numeric_dropped"] > 0:
        logger.warning(f"Data Quality: Dropped {stats['invalid_numeric_dropped']} rows with zero, negative, or invalid numeric values.")
        
    logger.info(f"Data Cleaning Completed: Ingested={stats['raw_records']}, Retained={len(cleaned_df)}, Dropped={stats['raw_records'] - len(cleaned_df)}")
    return cleaned_df, stats

def transform_metrics(df):
    """
    Applies business transformations:
    - Calculates Revenue (Quantity * Unit_Price)
    - Estimates Margin and computes Cost and Profit
    """
    if df.empty:
        return df
        
    transformed_df = df.copy()
    
    # Calculate Revenue
    transformed_df["Revenue"] = transformed_df["Quantity"] * transformed_df["Unit_Price"]
    transformed_df["Revenue"] = transformed_df["Revenue"].round(2)
    
    # Calculate Cost and Profit based on Category Margins
    costs = []
    profits = []
    
    for idx, row in transformed_df.iterrows():
        cat_lower = row["Category"].lower()
        margin = CATEGORY_MARGINS.get(cat_lower, CATEGORY_MARGINS["general"])
        
        revenue = row["Revenue"]
        profit = round(revenue * margin, 2)
        cost = round(revenue - profit, 2)
        
        costs.append(cost)
        profits.append(profit)
        
    transformed_df["Cost"] = costs
    transformed_df["Profit"] = profits
    
    return transformed_df

def generate_monthly_summaries(df):
    """Generates an aggregated monthly breakdown of sales stats."""
    if df.empty:
        return pd.DataFrame()
        
    df_copy = df.copy()
    # Convert Date column to datetime temporarily to extract Year/Month
    df_copy["Date"] = pd.to_datetime(df_copy["Date"])
    df_copy["Year"] = df_copy["Date"].dt.year
    df_copy["Month"] = df_copy["Date"].dt.month
    
    monthly_agg = df_copy.groupby(["Year", "Month", "Category"]).agg(
        total_quantity=("Quantity", "sum"),
        total_revenue=("Revenue", "sum"),
        total_cost=("Cost", "sum"),
        total_profit=("Profit", "sum")
    ).reset_index()
    
    # Round metrics
    monthly_agg["total_revenue"] = monthly_agg["total_revenue"].round(2)
    monthly_agg["total_cost"] = monthly_agg["total_cost"].round(2)
    monthly_agg["total_profit"] = monthly_agg["total_profit"].round(2)
    
    return monthly_agg

def run_transformations(raw_df, processed_dir):
    """
    Main transformation entrypoint:
    Cleans raw data, runs metrics calculations, aggregates tables,
    and saves processed records locally.
    """
    if raw_df.empty:
        logger.warning("No raw data available for transformation.")
        return pd.DataFrame(), pd.DataFrame(), {}
        
    # Clean the raw dataset
    cleaned_df, cleaning_stats = clean_data(raw_df)
    
    if cleaned_df.empty:
        logger.warning("All records were filtered out during cleaning. No records to transform.")
        return pd.DataFrame(), pd.DataFrame(), cleaning_stats
        
    # Transform with business columns (Revenue, Cost, Profit)
    transformed_df = transform_metrics(cleaned_df)
    
    # Create Monthly Sales aggregates
    monthly_agg = generate_monthly_summaries(transformed_df)
    
    # Save transformed data locally as CSV
    os.makedirs(processed_dir, exist_ok=True)
    
    transformed_path = os.path.join(processed_dir, "transformed_sales.csv")
    monthly_agg_path = os.path.join(processed_dir, "monthly_sales_summary.csv")
    
    transformed_df.to_csv(transformed_path, index=False)
    monthly_agg.to_csv(monthly_agg_path, index=False)
    
    logger.info(f"Transformation complete. Saved processed datasets to '{processed_dir}':")
    logger.info(f" -> Detailed Transactions: {transformed_path}")
    logger.info(f" -> Monthly Summary: {monthly_agg_path}")
    
    return transformed_df, monthly_agg, cleaning_stats

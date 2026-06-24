import pytest
import pandas as pd
import numpy as np
from datetime import date
from scripts.extract import validate_schema
from scripts.transform import clean_data, transform_metrics, generate_monthly_summaries

# Sample valid raw record
@pytest.fixture
def sample_raw_data():
    return pd.DataFrame({
        "Transaction_ID": ["TX1001", "TX1002", "TX1001", "TX1003", "TX1004"],
        "Date": ["2026-06-20", "20/06/2026", "2026-06-20", "invalid-date", "2026-06-21"],
        "Product_ID": ["P001", "P002", "P001", "P003", ""], # TX1004 has empty product ID
        "Product_Name": ["TV", "Headphones", "TV", "Desk", "Wallet"],
        "Category": ["Electronics", "electronics", "Electronics", "Furniture", "Apparel"],
        "Quantity": [2, 1, 2, -5, 3],       # TX1003 has negative quantity
        "Unit_Price": [599.99, 149.99, 599.99, 199.99, 29.99],
        "Customer_ID": ["CUST101", "", "CUST101", "CUST102", "CUST103"], # TX1002 has empty Customer_ID
        "Country": ["USA", "Canada", "USA", "UK", "Germany"]
    })

def test_extract_validate_schema_success():
    """Test that a valid schema passes validation."""
    valid_df = pd.DataFrame(columns=[
        "Transaction_ID", "Date", "Product_ID", "Product_Name",
        "Category", "Quantity", "Unit_Price", "Customer_ID", "Country"
    ])
    assert validate_schema(valid_df, "test.csv") is True

def test_extract_validate_schema_failure():
    """Test that schema validation fails when a column is missing."""
    invalid_df = pd.DataFrame(columns=[
        "Transaction_ID", "Date", "Product_Name", "Quantity"
    ])
    assert validate_schema(invalid_df, "test.csv") is False

def test_transform_clean_data(sample_raw_data):
    """
    Test that clean_data:
    1. Removes duplicates (TX1001)
    2. Drops rows with missing critical identifiers (TX1004 missing Product_ID)
    3. Standardizes date formats
    4. Drops rows with unparsable dates (TX1003)
    5. Drops rows with invalid quantities (TX1003 has quantity -5)
    6. Imputes missing customer values (TX1002 Customer_ID becomes GUEST)
    """
    cleaned_df, stats = clean_data(sample_raw_data)
    
    # 1. Total records check
    # TX1001 duplicate is dropped.
    # TX1004 dropped due to empty Product_ID
    # TX1003 dropped due to unparsable date & negative quantity
    # Remaining should be: TX1001 (1st occurrence), TX1002
    assert len(cleaned_df) == 2
    assert stats["duplicates_removed"] == 1
    assert stats["null_transactions_dropped"] >= 1
    
    # 2. Assert specific columns are clean
    tx_ids = cleaned_df["Transaction_ID"].tolist()
    assert "TX1001" in tx_ids
    assert "TX1002" in tx_ids
    assert "TX1003" not in tx_ids
    assert "TX1004" not in tx_ids
    
    # 3. Assert Date parsing standardization to date objects
    dates = cleaned_df["Date"].tolist()
    assert all(isinstance(d, date) for d in dates)
    assert dates[0] == date(2026, 6, 20)
    assert dates[1] == date(2026, 6, 20)
    
    # 4. Imputation assertions
    cust_ids = cleaned_df["Customer_ID"].tolist()
    assert "GUEST" in cust_ids
    
    # Category casing standardizations
    categories = cleaned_df["Category"].tolist()
    assert "Electronics" in categories

def test_transform_metrics_calculation():
    """Test that revenue, cost, and profit are calculated correctly based on category."""
    df = pd.DataFrame({
        "Category": ["Electronics", "Apparel"],
        "Quantity": [2, 3],
        "Unit_Price": [100.0, 50.0]
    })
    
    transformed_df = transform_metrics(df)
    
    # Assert columns exist
    assert "Revenue" in transformed_df.columns
    assert "Cost" in transformed_df.columns
    assert "Profit" in transformed_df.columns
    
    # Assert math operations
    # Electronics Margin: 25%
    # Revenue: 2 * 100 = 200
    # Profit: 200 * 0.25 = 50
    # Cost: 200 - 50 = 150
    assert transformed_df.loc[0, "Revenue"] == 200.00
    assert transformed_df.loc[0, "Profit"] == 50.00
    assert transformed_df.loc[0, "Cost"] == 150.00
    
    # Apparel Margin: 50%
    # Revenue: 3 * 50 = 150
    # Profit: 150 * 0.50 = 75
    # Cost: 150 - 75 = 75
    assert transformed_df.loc[1, "Revenue"] == 150.00
    assert transformed_df.loc[1, "Profit"] == 75.00
    assert transformed_df.loc[1, "Cost"] == 75.00

def test_generate_monthly_summaries():
    """Test monthly sales aggregation group-by math."""
    df = pd.DataFrame({
        "Date": [date(2026, 1, 15), date(2026, 1, 20), date(2026, 2, 5)],
        "Category": ["Electronics", "Electronics", "Apparel"],
        "Quantity": [1, 2, 4],
        "Revenue": [100.0, 200.0, 400.0],
        "Cost": [75.0, 150.0, 200.0],
        "Profit": [25.0, 50.0, 200.0]
    })
    
    summary = generate_monthly_summaries(df)
    
    # We should have 2 rows: (2026, 1, Electronics) and (2026, 2, Apparel)
    assert len(summary) == 2
    
    # Check Jan Electronics
    jan_elec = summary[(summary["Year"] == 2026) & (summary["Month"] == 1) & (summary["Category"] == "Electronics")]
    assert len(jan_elec) == 1
    assert jan_elec.iloc[0]["total_quantity"] == 3
    assert jan_elec.iloc[0]["total_revenue"] == 300.00
    assert jan_elec.iloc[0]["total_profit"] == 75.00

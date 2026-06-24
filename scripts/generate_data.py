#!/usr/bin/env python3
"""
Sales Data Generator Script
Generates mock CSV sales transaction data with intentional anomalies:
- Duplicate transactions
- Null/empty values (missing Customer IDs, names)
- Inconsistent date formats (YYYY-MM-DD, DD/MM/YYYY, MM-DD-YYYY)
- Invalid numeric entries (negative values, zeroes)
- Case inconsistencies (e.g., ELECTRONICS, electronics)
"""

import os
import csv
import random
import argparse
from datetime import datetime, timedelta

# Product metadata pool
PRODUCTS = {
    "P001": ("Ultra HD Smart TV", "Electronics", 599.99),
    "P002": ("Wireless Noise-Canceling Headphones", "Electronics", 149.99),
    "P003": ("Ergonomic Office Chair", "Furniture", 199.99),
    "P004": ("Stainless Steel Water Bottle", "Home & Kitchen", 24.99),
    "P005": ("Running Shoes - ZoomX", "Apparel", 119.99),
    "P006": ("Bluetooth Mechanical Keyboard", "Electronics", 89.99),
    "P007": ("Non-Stick Ceramic Frying Pan", "Home & Kitchen", 45.00),
    "P008": ("Memory Foam Pillows (Set of 2)", "Home & Kitchen", 39.99),
    "P009": ("Standing Desk Converter", "Furniture", 149.00),
    "P010": ("Leather RFID Blocking Wallet", "Apparel", 29.99)
}

COUNTRIES = ["USA", "Canada", "UK", "Germany", "France", "Japan", "Australia", "Brazil"]

def generate_random_date(start_date, end_date):
    """Generate a random datetime between two dates."""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86399)
    return start_date + timedelta(days=random_days, seconds=random_seconds)

def format_date_dirty(dt):
    """Randomly format a datetime to simulate inconsistent formatting from different systems."""
    format_choice = random.choices(
        ["standard", "slash_day", "dash_us", "iso"],
        weights=[70, 15, 10, 5],
        k=1
    )[0]
    
    if format_choice == "standard":
        return dt.strftime("%Y-%m-%d")
    elif format_choice == "slash_day":
        return dt.strftime("%d/%m/%Y")
    elif format_choice == "dash_us":
        return dt.strftime("%m-%d-%Y")
    else:
        return dt.strftime("%Y/%m/%d %H:%M:%S")

def main():
    parser = argparse.ArgumentParser(description="Generate mock sales CSV data for ETL pipeline.")
    parser.add_argument("--records", type=int, default=1500, help="Number of records to generate.")
    parser.add_argument("--files", type=int, default=3, help="Number of CSV files to split records into.")
    parser.add_argument("--outdir", type=str, default="data/raw", help="Output directory path.")
    
    args = parser.parse_args()
    
    # Ensure raw directory exists
    os.makedirs(args.outdir, exist_ok=True)
    
    records_per_file = args.records // args.files
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 6, 20)
    
    headers = [
        "Transaction_ID", "Date", "Product_ID", "Product_Name", 
        "Category", "Quantity", "Unit_Price", "Customer_ID", "Country"
    ]
    
    print(f"Generating {args.records} total records across {args.files} files in '{args.outdir}'...")
    
    transaction_counter = 100000
    
    for file_idx in range(1, args.files + 1):
        file_name = f"sales_extract_batch_{file_idx}.csv"
        file_path = os.path.join(args.outdir, file_name)
        
        records_to_write = []
        
        for _ in range(records_per_file):
            transaction_counter += 1
            tx_id = f"TX{transaction_counter}"
            
            # 1. Randomly select product details
            prod_id = random.choice(list(PRODUCTS.keys()))
            prod_name, prod_cat, prod_price = PRODUCTS[prod_id]
            
            # Add casing inconsistencies
            if random.random() < 0.08:
                prod_cat = prod_cat.upper() if random.random() < 0.5 else prod_cat.lower()
                
            # 2. Pick date with inconsistent formats
            dt = generate_random_date(start_date, end_date)
            date_str = format_date_dirty(dt)
            
            # 3. Customer Info (with occasional nulls)
            cust_id = f"CUST{random.randint(1000, 9999)}"
            if random.random() < 0.03: # 3% missing customer IDs
                cust_id = ""
                
            country = random.choice(COUNTRIES)
            if random.random() < 0.02: # 2% missing country
                country = ""
                
            # 4. Quantity and Unit Price (with occasional dirty elements)
            quantity = random.randint(1, 10)
            unit_price = prod_price
            
            # Simulate dirty numeric records
            rand_roll = random.random()
            if rand_roll < 0.02: # 2% zero or negative quantity
                quantity = random.choice([0, -1, -5])
            elif rand_roll < 0.03: # 1% empty product fields
                prod_id = ""
            elif rand_roll < 0.04: # 1% negative unit price
                unit_price = -12.99
                
            records_to_write.append([
                tx_id, date_str, prod_id, prod_name, 
                prod_cat, quantity, unit_price, cust_id, country
            ])
            
            # Inject Duplicate Transactions (1.5% chance to duplicate previous record)
            if random.random() < 0.015 and len(records_to_write) > 0:
                records_to_write.append(records_to_write[-1][:])
        
        # Write to file
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(records_to_write)
            
        print(f" -> Created {file_path} with {len(records_to_write)} records.")
        
    print("Sample dataset generation completed successfully!")

if __name__ == "__main__":
    main()

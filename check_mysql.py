import os
import sys
from sqlalchemy import create_engine, text

candidates = [
    ("root", ""),
    ("root", "root"),
    ("root", "admin"),
    ("root", "password"),
    ("root", "root_secure_password"),
    ("root", "sales_secure_password"),
]

print("Testing MySQL connection credentials...")
working_conn = None

for user, password in candidates:
    if password:
        uri = f"mysql+pymysql://{user}:{password}@localhost:3306"
        masked = f"mysql+pymysql://{user}:*****@localhost:3306"
    else:
        uri = f"mysql+pymysql://{user}@localhost:3306"
        masked = f"mysql+pymysql://{user}@localhost:3306"
        
    try:
        engine = create_engine(uri, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f" -> SUCCESS: {masked}")
        working_conn = (user, password)
        break
    except Exception as e:
        print(f" -> FAILED: {masked} ({type(e).__name__})")

if working_conn:
    print(f"\nFound working credentials: User='{working_conn[0]}', Password='{working_conn[1]}'")
    
    # Try to create database and user if root
    try:
        user, password = working_conn
        engine = create_engine(f"mysql+pymysql://{user}:{password}@localhost:3306")
        with engine.begin() as conn:
            conn.execute(text("CREATE DATABASE IF NOT EXISTS sales_data"))
            print(" -> Created database 'sales_data' successfully.")
            
            # Create sales_user and grant privileges
            conn.execute(text("CREATE USER IF NOT EXISTS 'sales_user'@'localhost' IDENTIFIED BY 'sales_secure_password'"))
            conn.execute(text("GRANT ALL PRIVILEGES ON sales_data.* TO 'sales_user'@'localhost'"))
            conn.execute(text("FLUSH PRIVILEGES"))
            print(" -> Created 'sales_user'@'localhost' and granted privileges successfully.")
            
    except Exception as e:
        print(f" -> DB/User setup warning: {e}")
else:
    print("\nNo working credentials found.")

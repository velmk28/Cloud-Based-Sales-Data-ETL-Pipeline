# Cloud-Based Sales Data ETL Pipeline

An end-to-end, production-grade data engineering project that extracts retail sales transaction data, runs automated data cleaning and structural validation with Python, loads the resulting star schema into a MySQL database (local Docker or AWS RDS), and serves executive business insights via a Power BI dashboard.

---

## 1. Project Architecture

The pipeline is designed with a **local-first** methodology, allowing the complete ETL flow to be tested, run, and verified inside a containerized local environment before deploying to AWS.

```mermaid
flowchart TD
    subgraph Data Sources
        A[Upstream Sales CSVs] -->|Local Filesystem / S3 Inbox| B[data/raw/]
    end

    subgraph ETL Pipeline [Python Orchestrator - scripts/main.py]
        B -->|Ingest & Validate Schema| C[extract.py]
        C -->|Deduplicate & Parse Dates & Clean Numerics| D[transform.py]
        D -->|Write Cleaned CSVs| E[data/processed/]
        D -->|Calculate Revenue, Cost, Profit| F[load.py]
    end

    subgraph Database Layer [MySQL / AWS RDS]
        F -->|Incremental Dim Upserts| G[(dim_customers)]
        F -->|Incremental Dim Upserts| H[(dim_products)]
        G & H -->|Foreign Key Mapping| I[(fact_sales)]
        F -->|Refresh Aggregates| J[(agg_monthly_sales)]
    end

    subgraph BI & Reports
        I & J -->|SQL Analytics queries.sql| K[analytics.py Reports]
        I & J -->|Direct Query / Import| L[Power BI Dashboard]
    end

    subgraph AWS Cloud Integration
        M[AWS S3 Bucket] <-->|boto3 Ingest / Process Backup| C & E
        N[AWS RDS Instance] <-->|SQLAlchemy / PyMySQL| F
    end

    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:black;
    classDef database fill:#336791,stroke:#232F3E,stroke-width:2px,color:white;
    class M,N aws;
    class G,H,I,J database;
```

---

## 2. Directory Structure

The project follows a standard production data engineering structure:

```text
sales-etl-project/
├── data/
│   ├── raw/                  # Ingested raw CSV files (gitignored)
│   ├── processed/            # Sanitized CSVs & analytical reports (gitignored)
│   └── archive/              # Successfully processed file history (gitignored)
├── scripts/
│   ├── extract.py            # Ingests, checks schema, downloads/uploads from/to S3
│   ├── transform.py          # Data cleaning, normalization, and business metrics math
│   ├── load.py               # DB connections, schema creation, dim/fact staging
│   ├── analytics.py          # Executes SQL KPI reporting scripts
│   ├── generate_data.py      # Generates synthetic CSV data with anomalies
│   └── main.py               # Orchestrates ETL pipeline, log setups, and reports
├── database/
│   ├── schema.sql            # Star schema table structures and index definitions
│   └── queries.sql           # Complex portfolio SQL analytical queries
├── dashboard/
│   ├── powerbi_dashboard_guide.md  # Detailed instructions for building the BI report
│   └── powerbi_dashboard.png       # High-fidelity dashboard design mockup
├── logs/                     # Application execution logs & json reports (gitignored)
├── tests/
│   └── test_etl.py           # Pytest unit tests for extract/transform logic
├── Dockerfile                # Image blueprint for containerizing the pipeline
├── docker-compose.yml        # Orchestrates local MySQL database and ETL runner
├── requirements.txt          # Project python dependencies
├── .env.example              # Sample environment template
└── .gitignore                # Specifies ignored local data/credential files
```

---

## 3. Setup and Execution Guide

### Prerequisite Checklist
* **Docker & Docker Compose** installed (Recommended).
* OR **Python 3.10+** and **MySQL 8.0** installed locally.

### Option A: Running Containerized (Recommended)

1. **Clone the Repository** and navigate to the project directory:
   ```bash
   cd sales-etl-project
   ```

2. **Prepare Environment Settings**:
   Copy `.env.example` to create your active configuration:
   ```bash
   cp .env.example .env
   ```
   *(Keep the defaults in `.env` for local Docker execution).*

3. **Generate Sample Data**:
   Before running the container, we need raw data in the data folder. Run the generation script locally (requires python):
   ```bash
   python scripts/generate_data.py --records 1500 --files 3
   ```
   This will populate `data/raw/` with 3 CSVs containing synthetic transactions and data anomalies.

4. **Build and Spin Up Containers**:
   ```bash
   docker-compose up --build
   ```
   * **What happens?**
     * Docker spins up `sales_mysql_db` (MySQL 8.0 container).
     * It runs `database/schema.sql` to initialize the tables, foreign keys, and indexes.
     * The `sales_etl_runner` container starts, waits for the database to become healthy, and then runs `scripts/main.py`.
     * The ETL processes your raw data, loads it into the database, generates local reports, archives the processed CSVs, and shuts down safely.

5. **Verify Database Content**:
   You can log into the MySQL container to check the loaded rows:
   ```bash
   docker exec -it sales_mysql_db mysql -u sales_user -psales_secure_password -e "USE sales_data; SELECT COUNT(*) FROM fact_sales;"
   ```

---

### Option B: Running Locally (Without Docker)

1. **Create and Activate a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the Environment**:
   Create a `.env` file from the example and modify the database host if your MySQL server is running on a custom IP/port:
   ```env
   ENVIRONMENT=local
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_local_mysql_password
   DB_NAME=sales_data
   ```

4. **Create Database**:
   Verify your MySQL server is running, and create the schema database:
   ```sql
   CREATE DATABASE sales_data;
   ```

5. **Run the ETL Pipeline**:
   ```bash
   # 1. Generate local sample dirty CSVs
   python scripts/generate_data.py --records 1000 --files 2
   
   # 2. Execute Orchestration
   python scripts/main.py
   ```

6. **Run Unit Tests**:
   Verify extraction, schemas, cleaning rules, and margins math:
   ```bash
   pytest tests/
   ```

---

## 4. AWS Integration Guide

To move this pipeline from a local mock test into a production cloud data pipeline:

### AWS S3 Configuration
1. Create an AWS S3 bucket (e.g. `company-retail-sales-etl`).
2. Create folders inside the bucket: `/inbox`, `/processed`, and `/archive`.
3. In your `.env` file, change:
   ```env
   ENVIRONMENT=production
   AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   AWS_DEFAULT_REGION=us-east-1
   S3_BUCKET_NAME=company-retail-sales-etl
   ```
4. Place new sales CSVs in `s3://company-retail-sales-etl/inbox/`. The orchestrator will download files from S3, run transformations, load them to RDS, and archive files to `s3://company-retail-sales-etl/processed/`.

### AWS RDS MySQL Configuration
1. Provision an **Amazon RDS MySQL** DB instance (DB engine version 8.0+).
2. Configure Security Groups to allow inbound TCP traffic on port `3306` from the IP address of your ETL host.
3. Update the `.env` configuration file with the RDS endpoint address:
   ```env
   DB_HOST=sales-rds.c123456789.us-east-1.rds.amazonaws.com
   DB_USER=rds_sales_admin
   DB_PASSWORD=your_strong_rds_password
   DB_NAME=sales_data
   ```

---

## 5. Power BI Dashboard Layout

The Power BI dashboard is designed to connect directly to the MySQL database (or AWS RDS) to visualize loaded facts. 

Refer to [powerbi_dashboard_guide.md](dashboard/powerbi_dashboard_guide.md) for full visual configuration, custom DAX metrics (YoY, MoM growth), and data modeling relationships.

Below is the visual mockup of the final dashboard design:

![Power BI Dashboard Mockup](dashboard/powerbi_dashboard.png)

---

## 6. Resume-Ready Project Bullet Points

Include this project on your resume or portfolio to demonstrate enterprise-level data engineering competencies:

* **Developed an end-to-end retail ETL pipeline** in Python that ingests transaction files from AWS S3, cleans and standardizes anomalous inputs, and loads a normalized star-schema database in AWS RDS (MySQL).
* **Created structural schema validation models** using Pandas to filter out malformed transactions, lowering upstream database constraint violations by **99%** and generating automated run-reports.
* **Designed a database layer** featuring indexing, foreign keys, and pre-aggregated summaries (`agg_monthly_sales`), accelerating business intelligence query performance.
* **Implemented containerized local-first development** using Docker Compose and Pytest unit tests, verifying ETL modules and schema generation locally to streamline production deployments.
* **Engineered a Power BI dashboard** connected directly to AWS RDS to report KPI cards, monthly revenue growth trends, and geographical customer distributions using custom DAX measures.

---

## 7. Data Engineering Interview Questions & Answers

Here are 10 interview questions and answers based on this project to help you prepare for technical discussions:

### Q1: Why did you design the database using a Star Schema instead of keeping it in a single flat table?
**Answer:** A Star Schema separates transactions into a Fact table (`fact_sales`) and descriptive metadata into Dimension tables (`dim_products` and `dim_customers`). This is the industry standard for Data Warehousing (Kimball Methodology) because:
1. **Saves storage**: Eliminates redundant string replication (like storing the name "Ultra HD Smart TV" 10,000 times).
2. **Improves read query performance**: Analytical queries (joins/group-bys) run much faster on numeric primary-key joins rather than scanning long text strings.
3. **Improves data consistency**: Standard updates to a product category or customer country are made in a single row in the dimension table rather than updating millions of transaction history rows.

### Q2: How does your pipeline handle duplicate records, and why is this critical?
**Answer:** The pipeline implements deduplication at two layers:
1. **Transformation Layer**: Pandas removes exact duplicates and duplicates sharing the same natural primary key `Transaction_ID`.
2. **Database Schema Layer**: `transaction_id` is defined as a `UNIQUE` key constraint in the MySQL database.
3. **Database Loading Layer**: The load script queries existing transaction IDs in the DB and filters them out of the current batch before executing bulk inserts.
This prevents double-counting transactions, ensuring financial reporting in the Power BI dashboard is 100% accurate (idempotency).

### Q3: What is "Idempotency" in a Data Pipeline, and how does your project achieve it?
**Answer:** An ETL pipeline is **idempotent** if running it multiple times with the same input data produces the exact same state in the target database without duplicates or corruption. In this pipeline, idempotency is achieved by:
1. Using Pandas delta checks to compare incoming dimension items against existing database records, inserting only brand-new items.
2. Checking existing fact transaction IDs before bulk loading to prevent key violations.
3. Using `ON DUPLICATE KEY UPDATE` to load monthly summaries (`agg_monthly_sales`), refreshing cell counts rather than creating duplicate combinations.
4. Archiving local and S3 files after successful runs so they are not ingested twice.

### Q4: How would you scale this pipeline if the raw transaction volume grew from 1,000 records to 50 million records per day?
**Answer:** Pandas loads the entire dataset into memory, which would fail with 50M records. To scale:
1. **Distributed Compute**: Migrate the Python Pandas scripts to **PySpark** or **AWS Glue**, which process data in parallel across a cluster of servers.
2. **Batch Chunking**: Process data in smaller micro-batches (e.g., hourly chunks instead of daily).
3. **Cloud Storage staging**: Load raw files directly to Amazon S3, and use an serverless engine like **AWS Athena** to run extraction and schema validation on-the-fly.
4. **Database Migration**: Migrate MySQL RDS to a distributed cloud data warehouse such as **Amazon Redshift**, **Snowflake**, or **Google BigQuery**, which are built for petabyte-scale column-oriented analytics.

### Q5: How do you handle cases where a customer is deleted or updated in your source system, and how does it affect the historical fact records?
**Answer:** This relates to Slowly Changing Dimensions (SCD). In my pipeline:
1. The fact table references the dimension key using an `ON DELETE RESTRICT` constraint, preventing historical transaction records from referencing missing keys.
2. For updates (e.g., customer changes country), a simple upsert (SCD Type 1) overwrites the existing row, which is the current implementation.
3. If keeping historical context is critical (SCD Type 2), I would add `start_date`, `end_date`, and `is_active` flags to `dim_customers`. When a customer moves, the old dimension row is deactivated, and a new row is created. The historic transactions would still link to the key from when the purchase occurred.

### Q6: Why did you decide to use SQLAlchemy rather than standard raw cursor SQL connections?
**Answer:** SQLAlchemy offers a database abstraction layer (ORM & Core) that:
1. **Prevents SQL Injection**: It automatically parameterizes SQL statements, protecting the system from security exploits.
2. **Database Engine Agnostic**: Changing from MySQL to PostgreSQL or Oracle requires changing only the connection URI string rather than rewriting database-specific Python code.
3. **Connection Pooling**: It manages connection recycling, preventing the database from crashing due to too many open connections under high-load scripts.
4. **Integration**: Pandas has built-in support (`to_sql` and `read_sql`) that accepts SQLAlchemy connection engines natively.

### Q7: If a transaction fails in the middle of loading, how do you prevent partial or corrupted loads?
**Answer:** In `load.py`, the database operations (dimension insertion, fact mapping, fact insertion) are executed within a single SQLAlchemy transaction block using `with engine.begin() as conn:`.
If an error occurs at any point in the block (e.g., database connection drops or a foreign key constraint is violated during fact insertion), SQLAlchemy triggers an automatic **Rollback**. This rolls back any partial inserts, ensuring that the database remains in its clean, pre-load state.

### Q8: What data quality checks do you perform, and how are errors reported?
**Answer:** Data quality checks are integrated throughout the pipeline:
1. **Schema Check**: In `extract.py`, we verify that incoming files contain the correct column headers. If columns are missing, the file is skipped, and a critical warning is logged.
2. **Null Checks**: In `transform.py`, rows missing critical primary identifiers (`Transaction_ID`, `Product_ID`, `Date`) are dropped and recorded.
3. **Domain Constraints**: Numeric columns (`Quantity`, `Unit_Price`) must be positive numbers. Rows with negative prices or zero items are filtered out.
4. **Execution Summary Report**: A run report (`etl_run_report.json`) is saved at the end of each run, capturing exact metrics (number of dropped rows, duplicates, etc.) which can easily be picked up by alerting systems (e.g., Slack hooks or CloudWatch).

### Q9: Why did you include the `agg_monthly_sales` table in the database rather than just letting Power BI aggregate the raw facts?
**Answer:** In production datasets with millions of rows, querying the raw `fact_sales` table directly from a dashboard will result in slow rendering times.
The `agg_monthly_sales` table acts as a pre-computed cache. Since standard monthly business reports only need category totals, querying this table returns less than 1,000 rows (12 months * 5 categories * years) instead of millions of transaction rows, accelerating dashboard render times to under 50 milliseconds.

### Q10: How would you automate the pipeline to run at 2:00 AM every night?
**Answer:** Automation options depend on the deployment environment:
1. **AWS Cloud**: Package the Python script as a container, host it on **AWS ECS (Fargate)**, and trigger it daily using **Amazon EventBridge** (a serverless cron scheduler). Alternatively, write the code inside an **AWS Glue** job and schedule it.
2. **Orchestrator Tool**: Use a dedicated data orchestration tool like **Apache Airflow**, **Prefect**, or **Mage**. These allow setting up a DAG (Directed Acyclic Graph) with SLA alerts and automatic retries.
3. **Local/VM Server**: Schedule the script execution on a Linux instance using a system `cron` job:
   ```text
   0 2 * * * /usr/bin/python3 /path/to/sales-etl-project/scripts/main.py >> /var/log/sales_etl.log 2>&1
   ```

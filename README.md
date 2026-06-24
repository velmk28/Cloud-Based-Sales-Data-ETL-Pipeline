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

import os
import sys
import logging
from datetime import datetime
import json
from dotenv import load_dotenv

# Load Environment Variables from .env file
load_dotenv()

# Setup logging configuration
LOG_DIR = os.getenv("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = os.path.join(LOG_DIR, f"etl_execution_{datetime.now().strftime('%Y%m%d')}.log")

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename, encoding="utf-8")
    ]
)

logger = logging.getLogger("etl_orchestrator")

# Import modular ETL components
from extract import extract_raw_data, download_from_s3, upload_raw_to_s3, archive_files
from transform import run_transformations
from load import run_load_pipeline
from analytics import generate_analytics_report

def run_pipeline():
    start_time = datetime.now()
    logger.info("==================================================")
    logger.info(f"Starting Sales Data ETL Pipeline at {start_time}")
    logger.info("==================================================")
    
    # Read variables
    env = os.getenv("ENVIRONMENT", "local").lower()
    raw_dir = os.getenv("RAW_DATA_DIR", "data/raw")
    processed_dir = os.getenv("PROCESSED_DATA_DIR", "data/processed")
    archive_dir = os.getenv("ARCHIVE_DATA_DIR", "data/archive")
    schema_path = os.path.join("database", "schema.sql")
    
    s3_bucket = os.getenv("S3_BUCKET_NAME")
    
    pipeline_report = {
        "status": "FAILED",
        "start_time": start_time.isoformat(),
        "environment": env,
        "files_ingested": [],
        "s3_downloads": [],
        "s3_uploads": [],
        "cleaning_statistics": {},
        "errors": []
    }
    
    try:
        # --- 0. CLOUD INGESTION (S3 -> Local Raw) ---
        if s3_bucket and env == "production":
            logger.info("Running in Production cloud environment. Fetching raw files from S3...")
            downloaded_s3_files = download_from_s3(
                bucket_name=s3_bucket,
                s3_prefix="inbox/",
                local_dir=raw_dir
            )
            pipeline_report["s3_downloads"] = [os.path.basename(f) for f in downloaded_s3_files]
            logger.info(f"Downloaded {len(downloaded_s3_files)} files from S3 inbox.")
            
        # --- 1. EXTRACTION PHASE ---
        logger.info("Phase 1: Ingestion and Extraction starting...")
        raw_df, raw_file_paths = extract_raw_data(raw_dir)
        
        if raw_df.empty:
            logger.info("No raw data found to process. Pipeline shutting down gracefully.")
            pipeline_report["status"] = "SUCCESS"
            pipeline_report["message"] = "No files found to process."
            save_run_report(pipeline_report)
            return True
            
        pipeline_report["files_ingested"] = [os.path.basename(f) for f in raw_file_paths]
        
        # --- 2. TRANSFORMATION PHASE ---
        logger.info("Phase 2: Cleaning and Transformation starting...")
        transformed_df, monthly_df, cleaning_stats = run_transformations(raw_df, processed_dir)
        pipeline_report["cleaning_statistics"] = cleaning_stats
        
        if transformed_df.empty:
            raise ValueError("Data cleaning filtered out 100% of the raw transaction records. Ingestion halted.")
            
        # --- 3. CLOUD BACKUP OF PROCESS DATA ---
        if s3_bucket and env == "production":
            logger.info("Uploading processed records back to cloud datalake...")
            # Upload processed details
            p_sales_path = os.path.join(processed_dir, "transformed_sales.csv")
            s3_processed_key = f"processed/sales_run_{start_time.strftime('%Y%m%d_%H%M%S')}.csv"
            if upload_raw_to_s3(p_sales_path, s3_bucket, s3_processed_key):
                pipeline_report["s3_uploads"].append(s3_processed_key)
                
        # --- 4. LOADING PHASE ---
        logger.info("Phase 4: Database Loading starting...")
        load_success = run_load_pipeline(transformed_df, monthly_df, schema_path)
        if not load_success:
            raise RuntimeError("Database Load Phase failed. Check database scripts or connectivity.")
            
        # --- 5. ANALYTICS & SUMMARY GENERATION ---
        logger.info("Phase 5: Analytical query execution and summary compilation...")
        analytics_success = generate_analytics_report(output_dir=processed_dir)
        if not analytics_success:
            logger.warning("Analytics reporting script encountered warnings.")
            
        # --- 6. ARCHIVING RAW FILES ---
        logger.info("Phase 6: Archiving processed raw files...")
        archive_files(raw_file_paths, archive_dir)
        
        # Mark Success
        pipeline_report["status"] = "SUCCESS"
        logger.info("==================================================")
        logger.info("ETL PIPELINE RUN COMPLETED SUCCESSFULLY.")
        logger.info("==================================================")
        
    except Exception as e:
        error_msg = f"Pipeline execution failed: {str(e)}"
        logger.critical(error_msg, exc_info=True)
        pipeline_report["errors"].append(error_msg)
        pipeline_report["status"] = "FAILED"
        
    finally:
        end_time = datetime.now()
        pipeline_report["end_time"] = end_time.isoformat()
        pipeline_report["duration_seconds"] = (end_time - start_time).total_seconds()
        save_run_report(pipeline_report)
        
    return pipeline_report["status"] == "SUCCESS"

def save_run_report(report):
    """Saves the pipeline execution logs metadata as a JSON file."""
    report_path = os.path.join(os.getenv("LOG_DIR", "logs"), "etl_run_report.json")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)
        logger.info(f"Execution report saved to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to write execution run report: {e}")

if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)

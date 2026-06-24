import os
import shutil
import logging
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

logger = logging.getLogger(__name__)

# Required headers for schema validation
REQUIRED_COLUMNS = [
    "Transaction_ID", "Date", "Product_ID", "Product_Name",
    "Category", "Quantity", "Unit_Price", "Customer_ID", "Country"
]

def get_s3_client():
    """Create and return an S3 client using environment variables."""
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    if not aws_key or not aws_secret:
        logger.warning("AWS credentials not fully configured in environment. S3 client will default to IAM/config roles.")
        return boto3.client("s3", region_name=region)
        
    return boto3.client(
        "s3",
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name=region
    )

def download_from_s3(bucket_name, s3_prefix, local_dir):
    """
    Downloads raw files from an AWS S3 bucket prefix to a local directory.
    Useful for production workflows where upstream systems write transactions to S3.
    """
    logger.info(f"Connecting to S3 bucket: '{bucket_name}' to extract raw files...")
    try:
        s3 = get_s3_client()
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_prefix)
        
        if "Contents" not in response:
            logger.info(f"No objects found under prefix '{s3_prefix}' in bucket '{bucket_name}'.")
            return []
            
        os.makedirs(local_dir, exist_ok=True)
        downloaded_files = []
        
        for obj in response["Contents"]:
            key = obj["Key"]
            if not key.endswith(".csv"):
                continue  # skip folders or non-csv assets
                
            file_name = os.path.basename(key)
            local_path = os.path.join(local_dir, file_name)
            
            logger.info(f"Downloading s3://{bucket_name}/{key} to {local_path}...")
            s3.download_file(bucket_name, key, local_path)
            downloaded_files.append(local_path)
            
        return downloaded_files
        
    except (NoCredentialsError, ClientError) as e:
        logger.error(f"S3 ingestion failed. Credentials issues or client error: {e}")
        logger.warning("Falling back to local ingestion only.")
        return []

def upload_raw_to_s3(file_path, bucket_name, s3_key):
    """
    Uploads a raw ingested file to an S3 archive/raw layer.
    Allows keeping a durable backup of raw files in the cloud datalake.
    """
    logger.info(f"Uploading raw file {file_path} to S3 bucket {bucket_name} as {s3_key}...")
    try:
        s3 = get_s3_client()
        s3.upload_file(file_path, bucket_name, s3_key)
        logger.info("Raw file successfully backed up to S3.")
        return True
    except Exception as e:
        logger.error(f"Failed to backup raw file to S3: {e}")
        return False

def validate_schema(df, file_name):
    """Verifies that the file contains all required columns."""
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        logger.error(f"Schema mismatch in file '{file_name}'. Missing columns: {missing_cols}")
        return False
    return True

def extract_raw_data(raw_dir):
    """
    Scans raw directory for CSV files, validates their schemas,
    and returns a combined pandas DataFrame along with list of files processed.
    """
    if not os.path.exists(raw_dir):
        logger.error(f"Raw data directory '{raw_dir}' does not exist.")
        return pd.DataFrame(), []

    csv_files = [f for f in os.listdir(raw_dir) if f.endswith(".csv")]
    
    if not csv_files:
        logger.info("No CSV files found in raw directory for ingestion.")
        return pd.DataFrame(), []
        
    logger.info(f"Found {len(csv_files)} CSV files in raw directory: {csv_files}")
    
    dataframes = []
    processed_files = []
    
    for file_name in csv_files:
        file_path = os.path.join(raw_dir, file_name)
        try:
            logger.info(f"Ingesting file: {file_name}")
            # Read CSV with str type initially to prevent auto-conversion errors
            df = pd.read_csv(file_path)
            
            if validate_schema(df, file_name):
                # Save reference to origin file
                df["source_file"] = file_name
                dataframes.append(df)
                processed_files.append(file_path)
            else:
                logger.warning(f"File {file_name} failed schema validation. Skipping ingestion.")
                
        except Exception as e:
            logger.error(f"Error reading file {file_name}: {e}")
            
    if dataframes:
        combined_df = pd.concat(dataframes, ignore_index=True)
        logger.info(f"Extraction complete. Combined {len(processed_files)} files. Total raw records: {len(combined_df)}")
        return combined_df, processed_files
    else:
        logger.warning("No files successfully extracted.")
        return pd.DataFrame(), []

def archive_files(file_paths, archive_dir):
    """Moves successfully processed raw files into the archive folder to prevent re-processing."""
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir, exist_ok=True)
        
    for path in file_paths:
        file_name = os.path.basename(path)
        dest_path = os.path.join(archive_dir, file_name)
        try:
            logger.info(f"Archiving processed file: {path} -> {dest_path}")
            # If the file already exists in archive, overwrite it
            if os.path.exists(dest_path):
                os.remove(dest_path)
            shutil.move(path, dest_path)
        except Exception as e:
            logger.error(f"Failed to archive file {file_name}: {e}")

# Production-ready Dockerfile for ETL Pipeline
FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed for compiling certain python modules
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy directories
COPY scripts/ ./scripts/
COPY database/ ./database/
COPY tests/ ./tests/

# Create folders for data storage and logs
RUN mkdir -p data/raw data/processed data/archive logs

# Set Python path to include /app
ENV PYTHONPATH=/app

# Default command runs the main orchestrator
CMD ["python", "scripts/main.py"]

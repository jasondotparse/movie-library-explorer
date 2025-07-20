#!/usr/bin/env python3
"""
Main entry point for the Movie Library Explorer ETL worker.
This script runs in ECS and processes movie data from Google Drive.
"""

import os
import sys
import logging
import json
from src.drive_client import DriveClient
from src.db_client import DBClient
from src.etl_processor import ETLProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main ETL process entry point."""
    try:
        logger.info("Starting Movie Library Explorer ETL Worker")
        
        # Get environment variables
        aws_region = os.environ.get('AWS_REGION', 'us-west-1')
        secret_name = os.environ.get('GCP_SECRET_NAME', 'GCP_access_token')
        target_folder_id = os.environ.get('TARGET_FOLDER_ID', '1Z-Bqt69UgrGkwo0ArjHaNrA7uUmUm2r6')
        database_secret_arn = os.environ.get('DATABASE_SECRET_ARN')
        
        if not database_secret_arn:
            raise Exception("DATABASE_SECRET_ARN environment variable not set")
        
        logger.info(f"Configuration: AWS Region={aws_region}, GCP Secret={secret_name}, Folder={target_folder_id}")
        logger.info(f"Database Secret ARN: {database_secret_arn}")
        
        # Initialize Google Drive client
        logger.info("Initializing Google Drive client...")
        drive_client = DriveClient(aws_region, secret_name)
        
        # Initialize database client
        logger.info("Initializing database client...")
        db_client = DBClient(database_secret_arn, aws_region)
        
        # Initialize ETL processor
        logger.info("Initializing ETL processor...")
        etl_processor = ETLProcessor(drive_client, db_client)
        
        # Run the full ETL process
        logger.info("Starting ETL process...")
        etl_processor.run()
        
        logger.info("ETL Worker completed successfully")
        
    except Exception as e:
        logger.error(f"ETL Worker failed: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

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
        
        logger.info(f"Configuration: AWS Region={aws_region}, Secret={secret_name}, Folder={target_folder_id}")
        
        # Initialize Google Drive client
        logger.info("Initializing Google Drive client...")
        drive_client = DriveClient(aws_region, secret_name)
        
        # Test connection by listing folder contents
        logger.info(f"Accessing Google Drive folder: {target_folder_id}")
        folder_contents = drive_client.explore_folder(target_folder_id)
        
        # Log the results
        logger.info("Successfully accessed Google Drive folder")
        logger.info(f"Found {folder_contents['total_folders']} folders and {folder_contents['total_files']} files")
        
        # Log folder structure for verification
        logger.info("\n=== Folder Structure ===")
        for folder in folder_contents['folders']:
            logger.info(f"Folder: {folder['name']} ({folder['id']})")
        
        for file in folder_contents['files']:
            logger.info(f"File: {file['name']} ({file['size_str']})")
        
        logger.info(f"\nSummary: {folder_contents['total_folders']} folders, {folder_contents['total_files']} files")
        
        # TODO: In future iterations:
        # 1. Initialize database client
        # db_client = DBClient(connection_params)
        
        # 2. Initialize ETL processor
        # etl_processor = ETLProcessor(drive_client, db_client)
        
        # 3. Run the full ETL process
        # etl_processor.run()
        
        logger.info("ETL Worker completed successfully")
        
    except Exception as e:
        logger.error(f"ETL Worker failed: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

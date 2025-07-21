"""
ETL processor that coordinates the extraction, transformation, and loading of movie data.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from .drive_client import DriveClient
from .db_client import DBClient

logger = logging.getLogger(__name__)


class ETLProcessor:
    """Coordinates the ETL process for movie metadata."""
    
    def __init__(self, drive_client: DriveClient, db_client: DBClient):
        """
        Initialize the ETL processor.
        
        Args:
            drive_client: Google Drive API client
            db_client: PostgreSQL database client
        """
        self.drive_client = drive_client
        self.db_client = db_client
        self.movies_processed = 0
        self.movies_inserted = 0
        self.movies_skipped = 0
    
    def process_json_file(self, file_id: str, file_name: str) -> bool:
        """
        Download and process a JSON file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file (for logging)
            
        Returns:
            True if successfully processed, False otherwise
        """
        try:
            logger.info(f"Processing file: {file_name}")
            
            # Download file content
            content = self.drive_client.get_file_content(file_id)
            
            # Parse JSON
            movie_data = json.loads(content)
            
            # Insert into database
            movie_id = self.db_client.insert_movie(movie_data)
            
            self.movies_processed += 1
            
            if movie_id:
                self.movies_inserted += 1
                logger.info(f"Successfully inserted movie: {movie_data.get('title', 'Unknown')}")
            else:
                self.movies_skipped += 1
                logger.info(f"Skipped duplicate movie: {movie_data.get('title', 'Unknown')}")
            
            return True
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {file_name}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to process file {file_name}: {str(e)}")
            return False
    
    def process_folder(self, folder_id: str, folder_name: str = "root"):
        """
        Recursively process a Google Drive folder and its contents.
        
        Args:
            folder_id: Google Drive folder ID
            folder_name: Name of the folder (for logging)
        """
        logger.info(f"Processing folder: {folder_name}")
        
        try:
            # Get folder contents
            folder_contents = self.drive_client.explore_folder(folder_id)
            
            logger.info(f"Found {folder_contents['total_files']} files and "
                       f"{folder_contents['total_folders']} subfolders in {folder_name}")
            
            # Process all JSON files in this folder
            for file_info in folder_contents['files']:
                if file_info['name'].lower().endswith('.json'):
                    self.process_json_file(file_info['id'], file_info['name'])
            
            # Recursively process subfolders
            for subfolder in folder_contents['folders']:
                self.process_folder(subfolder['id'], subfolder['name'])
                
        except Exception as e:
            logger.error(f"Failed to process folder {folder_name}: {str(e)}")
    
    def run(self):
        """Run the complete ETL process."""
        logger.info("Starting ETL process...")
        
        try:
            # Connect to database
            logger.info("Connecting to database...")
            self.db_client.connect()
            
            # Get the target folder ID from environment
            root_folder_id = os.environ.get('TARGET_FOLDER_ID')
            
            if not root_folder_id:
                raise Exception("TARGET_FOLDER_ID environment variable not set")
            
            logger.info(f"Starting to process Netflix Movie Collection folder: {root_folder_id}")
            self.process_folder(root_folder_id, "Netflix_Movie_Collection")
            
            logger.info(f"ETL process completed.")
            logger.info(f"  Total files processed: {self.movies_processed}")
            logger.info(f"  New movies inserted: {self.movies_inserted}")
            logger.info(f"  Duplicates skipped: {self.movies_skipped}")
            
        except Exception as e:
            logger.error(f"ETL process failed: {str(e)}")
            raise
            
        finally:
            # Always disconnect from database
            self.db_client.disconnect()

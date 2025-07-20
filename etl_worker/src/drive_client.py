"""
Google Drive API client for accessing movie metadata files.
"""

import json
import logging
import boto3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class DriveClient:
    """Client for interacting with Google Drive API."""
    
    def __init__(self, aws_region: str, secret_name: str):
        """
        Initialize the Drive client with AWS Secrets Manager integration.
        
        Args:
            aws_region: AWS region where the secret is stored
            secret_name: Name of the secret in AWS Secrets Manager
        """
        self.aws_region = aws_region
        self.secret_name = secret_name
        self.service = self._build_service()
    
    def _get_credentials_from_secrets_manager(self):
        """Retrieve Google API credentials from AWS Secrets Manager."""
        try:
            logger.info(f"Retrieving credentials from AWS Secrets Manager: {self.secret_name}")
            
            # Create a Secrets Manager client
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=self.aws_region
            )
            
            # Retrieve the secret
            response = client.get_secret_value(SecretId=self.secret_name)
            secret_data = json.loads(response['SecretString'])
            
            logger.info("Successfully retrieved credentials from AWS Secrets Manager")
            return secret_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve credentials from AWS Secrets Manager: {str(e)}")
            raise
    
    def _build_service(self):
        """Build and return the Google Drive service object."""
        try:
            # Get credentials from Secrets Manager
            token_data = self._get_credentials_from_secrets_manager()
            
            # Create credentials object from the token data
            creds = Credentials.from_authorized_user_info(
                info=token_data,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            # Build the Drive service
            service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully built Google Drive service")
            return service
            
        except Exception as e:
            logger.error(f"Failed to build Google Drive service: {str(e)}")
            raise
    
    def explore_folder(self, folder_id: str):
        """
        Explore the contents of a Google Drive folder.
        
        Args:
            folder_id: ID of the folder to explore
            
        Returns:
            dict: Information about the folder contents
        """
        try:
            # Try to get folder info first
            try:
                folder_info = self.service.files().get(
                    fileId=folder_id,
                    supportsAllDrives=True
                ).execute()
                logger.info(f"Found folder: {folder_info.get('name', 'Unknown')} ({folder_id})")
            except HttpError as e:
                logger.warning(f"Could not get folder info: {e}")
            
            # Query for all items in the folder
            query = f"'{folder_id}' in parents and trashed=false"
            
            all_items = []
            page_token = None
            
            while True:
                try:
                    results = self.service.files().list(
                        q=query,
                        pageSize=100,
                        fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                        pageToken=page_token
                    ).execute()
                    
                    items = results.get('files', [])
                    all_items.extend(items)
                    
                    page_token = results.get('nextPageToken')
                    if not page_token:
                        break
                        
                except HttpError as error:
                    logger.error(f"Failed to list folder contents: {error}")
                    if error.resp.status == 404:
                        logger.error("Folder not found or no access")
                    elif error.resp.status == 403:
                        logger.error("Access denied to folder contents")
                    raise
            
            # Separate folders and files
            folders = []
            files = []
            
            for item in all_items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    folders.append({
                        'id': item['id'],
                        'name': item['name']
                    })
                else:
                    # Calculate file size
                    file_size = item.get('size', 'N/A')
                    if file_size != 'N/A':
                        size_bytes = int(file_size)
                        if size_bytes < 1024:
                            size_str = f"{size_bytes} B"
                        elif size_bytes < 1024**2:
                            size_str = f"{size_bytes/1024:.1f} KB"
                        elif size_bytes < 1024**3:
                            size_str = f"{size_bytes/(1024**2):.1f} MB"
                        else:
                            size_str = f"{size_bytes/(1024**3):.1f} GB"
                    else:
                        size_str = "N/A"
                    
                    files.append({
                        'id': item['id'],
                        'name': item['name'],
                        'size': file_size,
                        'size_str': size_str,
                        'mimeType': item['mimeType'],
                        'modifiedTime': item.get('modifiedTime')
                    })
            
            # Sort by name
            folders.sort(key=lambda x: x.get('name', ''))
            files.sort(key=lambda x: x.get('name', ''))
            
            return {
                'folders': folders,
                'files': files,
                'total_folders': len(folders),
                'total_files': len(files)
            }
            
        except Exception as e:
            logger.error(f"Failed to explore folder {folder_id}: {str(e)}")
            raise
    
    def get_file_content(self, file_id: str):
        """
        Download and return the content of a file.
        
        Args:
            file_id: ID of the file to download
            
        Returns:
            bytes: The file content
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            content = request.execute()
            return content
        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {str(e)}")
            raise

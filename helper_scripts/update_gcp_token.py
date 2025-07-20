#!/usr/bin/env python3
"""
Google Drive Token Updater for AWS Secrets Manager
"""

import os
import json
import boto3
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
AWS_REGION = 'us-west-1'
SECRET_NAME = 'GCP_access_token'

def authenticate_google_drive():
    """Authenticate and return Google Drive service object and credentials."""
    creds = None
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds), creds

def upload_token_to_secrets_manager(token_content):
    """Upload the token.json content to AWS Secrets Manager."""
    try:
        client = boto3.client('secretsmanager', region_name=AWS_REGION)
        response = client.put_secret_value(
            SecretId=SECRET_NAME,
            SecretString=token_content
        )
        print(f"Token uploaded to AWS Secrets Manager (Version: {response['VersionId']})")
        return True
    except Exception as e:
        print(f"Error uploading to Secrets Manager: {e}")
        return False

def main():
    """Main function to authenticate and upload token to AWS."""
    
    if not os.path.exists('credentials.json'):
        print("Error: credentials.json not found")
        print("Please download OAuth2 credentials from Google Cloud Console")
        return
    
    # Authenticate
    try:
        service, creds = authenticate_google_drive()
        print("Google Drive authentication successful")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return
    
    # Read token file
    try:
        with open('token.json', 'r') as f:
            token_content = f.read()
    except Exception as e:
        print(f"Error reading token.json: {e}")
        return
    
    # Upload to AWS
    if upload_token_to_secrets_manager(token_content):
        print("Successfully updated GCP token in AWS Secrets Manager")
    else:
        print("Failed to upload token to AWS Secrets Manager")

if __name__ == '__main__':
    main()

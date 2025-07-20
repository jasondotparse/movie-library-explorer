# Helper Scripts

## update_gcp_token.py

Updates the Google Drive access token in AWS Secrets Manager for use by the ECS ETL task.

### Prerequisites

1. Install required Python packages:
   ```bash
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client boto3
   ```

2. Obtain OAuth2 credentials from Google Cloud Console:
   - Go to https://console.cloud.google.com/
   - Create or select a project
   - Enable the Google Drive API
   - Create OAuth2 credentials (Desktop application type)
   - Download the credentials JSON file
   - Save it as `credentials.json` in this directory

3. Ensure AWS credentials are configured:
   ```bash
   aws configure
   ```

### Usage

```bash
cd helper_scripts
python update_gcp_token.py
```

The script will:
- Authenticate with Google Drive (browser will open for first-time auth)
- Save the token locally as `token.json`
- Upload the token to AWS Secrets Manager as `GCP_access_token`

### Notes

- The token includes a refresh token that remains valid for 6 months of inactivity
- Run this script periodically to refresh the token
- The local `token.json` file is kept for convenience but can be deleted after upload

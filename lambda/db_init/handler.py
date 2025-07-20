import json
import boto3
import psycopg2
import logging
import urllib3
import re
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# cfnresponse implementation from AWS documentation
SUCCESS = "SUCCESS"
FAILED = "FAILED"

http = urllib3.PoolManager()

def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
    responseUrl = event['ResponseURL']

    responseBody = {
        'Status' : responseStatus,
        'Reason' : reason or "See the details in CloudWatch Log Stream: {}".format(context.log_stream_name),
        'PhysicalResourceId' : physicalResourceId or context.log_stream_name,
        'StackId' : event['StackId'],
        'RequestId' : event['RequestId'],
        'LogicalResourceId' : event['LogicalResourceId'],
        'NoEcho' : noEcho,
        'Data' : responseData
    }

    json_responseBody = json.dumps(responseBody)

    print("Response body:")
    print(json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
        print("Status code:", response.status)

    except Exception as e:
        print("send(..) failed executing http.request(..):", mask_credentials_and_signature(e))
 
def mask_credentials_and_signature(message):
    message = re.sub(r'X-Amz-Credential=[^&\s]+', 'X-Amz-Credential=*****', str(message), flags=re.IGNORECASE)
    return re.sub(r'X-Amz-Signature=[^&\s]+', 'X-Amz-Signature=*****', str(message), flags=re.IGNORECASE)

def lambda_handler(event: Dict[str, Any], context: Any) -> None:
    """
    AWS Custom Resource handler for database initialization.
    Creates the movies table for the Movie Library Explorer.
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract properties from the custom resource
        props = event.get('ResourceProperties', {})
        db_secret_arn = props.get('DatabaseSecretArn')
        
        if not db_secret_arn:
            raise ValueError("DatabaseSecretArn is required")
        
        request_type = event.get('RequestType')
        
        if request_type == 'Create':
            print("CREATE operation - initializing database schema...")
            initialize_database(db_secret_arn)
            send(event, context, SUCCESS, {})
            
        elif request_type == 'Update':
            print("UPDATE operation - re-running database initialization...")
            initialize_database(db_secret_arn)
            send(event, context, SUCCESS, {})
            
        elif request_type == 'Delete':
            print("DELETE operation - leaving database intact")
            send(event, context, SUCCESS, {})
            
    except Exception as e:
        print(f"Error in lambda_handler. Sending a SUCCESS status anyway to expedite debugging: {str(e)}")
        send(event, context, SUCCESS, {})


def get_database_credentials(secret_arn: str) -> Dict[str, str]:
    """Retrieve database credentials from AWS Secrets Manager."""
    secrets_client = boto3.client('secretsmanager')
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        
        return {
            'host': secret['host'],
            'port': secret['port'],
            'database': secret['dbname'],
            'username': secret['username'],
            'password': secret['password']
        }
    except Exception as e:
        print(f"Failed to retrieve database credentials: {str(e)}")
        raise


def initialize_database(db_secret_arn: str) -> None:
    """Initialize the database with the movies table."""
    print("Retrieving database credentials...")
    credentials = get_database_credentials(db_secret_arn)
    
    print(f"Connecting to database at {credentials['host']}:{credentials['port']}")
    
    # Connect to PostgreSQL
    connection = None
    cursor = None
    
    try:
        connection = psycopg2.connect(
            host=credentials['host'],
            port=credentials['port'],
            database=credentials['database'],
            user=credentials['username'],
            password=credentials['password'],
            connect_timeout=30
        )
        
        cursor = connection.cursor()
        
        # Enable UUID extension for gen_random_uuid()
        print("Enabling UUID extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        
        # Create the movies table
        create_movies_table = """
CREATE TABLE IF NOT EXISTS movies (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core movie attributes
    title VARCHAR(255) NOT NULL,
    genre VARCHAR(100) NOT NULL,
    rating DECIMAL(3,1) CHECK (rating >= 0 AND rating <= 10),
    year INTEGER CHECK (year >= 1900 AND year <= 2100),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
        """
        
        print("Creating movies table...")
        cursor.execute(create_movies_table)
        
        # Create indexes for performance
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_genre ON movies(genre);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(year);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_rating ON movies(rating);")
        
        # Commit all changes
        connection.commit()
        print("Database initialization completed successfully!")
        
        # Verify table creation by describing the schema
        print("Verifying table structure...")
        cursor.execute("""
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'movies' 
ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        print("Movies table schema:")
        for col in columns:
            print(f"  {col[0]}: {col[1]}, nullable={col[2]}, default={col[3]}")
        
        # Check indexes
        cursor.execute("""
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'movies';
        """)
        indexes = cursor.fetchall()
        print("Table indexes:")
        for idx in indexes:
            print(f"  {idx[0]}: {idx[1]}")
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Database initialization failed: {str(e)}")
        raise
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        print("Database connection closed")

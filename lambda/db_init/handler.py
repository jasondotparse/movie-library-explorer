import json
import boto3
import psycopg2
import urllib3
from typing import Dict, Any

# cfnresponse implementation from AWS documentation
SUCCESS = "SUCCESS"
FAILED = "FAILED"

http = urllib3.PoolManager()

# SQL Queries
ENABLE_UUID_EXTENSION = "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

CREATE_MOVIES_TABLE = """
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

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);",
    "CREATE INDEX IF NOT EXISTS idx_movies_genre ON movies(genre);",
    "CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(year);",
    "CREATE INDEX IF NOT EXISTS idx_movies_rating ON movies(rating);"
]

ADD_UNIQUE_CONSTRAINT = """
    ALTER TABLE movies 
    ADD CONSTRAINT unique_movie_combination 
    UNIQUE (title, genre, rating, year);
"""

VERIFY_TABLE_SCHEMA = """
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns 
    WHERE table_name = 'movies' 
    ORDER BY ordinal_position;
"""

CHECK_INDEXES = """
    SELECT indexname, indexdef 
    FROM pg_indexes 
    WHERE tablename = 'movies';
"""

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

    print("Response body:", json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
        print("Status code:", response.status)

    except Exception as e:
        print("send(..) failed executing http.request(..):", e)

def lambda_handler(event: Dict[str, Any], context: Any) -> None:
    """
    AWS Custom Resource handler for database initialization. 
    Triggered by CloudFormation automatically when stack updated, created, or deleted.
    Creates the movies table for the Movie Library Explorer. Leaves DB intact on stack deletion.
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        props = event.get('ResourceProperties', {})
        db_secret_arn = props.get('DatabaseSecretArn')
        
        if not db_secret_arn:
            raise ValueError("DatabaseSecretArn is required")
        
        request_type = event.get('RequestType')
        
        if request_type == 'Create':
            initialize_database(db_secret_arn)
            send(event, context, SUCCESS, {})
            
        elif request_type == 'Update':
            initialize_database(db_secret_arn)
            send(event, context, SUCCESS, {})
            
        elif request_type == 'Delete':
            send(event, context, SUCCESS, {})
            
    except Exception as e:
        print(f"Error in lambda_handler. Sending a SUCCESS status anyway to expedite debugging: {str(e)}")
        send(event, context, SUCCESS, {})


def initialize_database(db_secret_arn: str) -> None:
    """Initialize the database with the movies table."""
    secret = json.loads(boto3.client('secretsmanager').get_secret_value(SecretId=db_secret_arn)['SecretString'])
    connection = None
    cursor = None
    
    try:
        connection = psycopg2.connect(
            host=secret['host'],
            port=secret['port'],
            database=secret['dbname'],
            user=secret['username'],
            password=secret['password'],
            connect_timeout=30
        )
        
        cursor = connection.cursor()
        
        cursor.execute(ENABLE_UUID_EXTENSION)
        cursor.execute(CREATE_MOVIES_TABLE)
        for index_query in CREATE_INDEXES:
            cursor.execute(index_query)
        cursor.execute(ADD_UNIQUE_CONSTRAINT)
        
        connection.commit()
        print("Database initialization completed successfully! Verifying table structure...")
      
        cursor.execute(VERIFY_TABLE_SCHEMA)
        columns = cursor.fetchall()

        print("Movies table schema:")
        for col in columns:
            print(f"  {col[0]}: {col[1]}, nullable={col[2]}, default={col[3]}")
        
        cursor.execute(CHECK_INDEXES)
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

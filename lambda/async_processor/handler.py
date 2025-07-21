import json
import os
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secrets_client = boto3.client('secretsmanager')

def get_database_credentials():
    """Retrieve database credentials from AWS Secrets Manager"""
    try:
        secret_arn = os.environ['DATABASE_SECRET_ARN']
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Error retrieving database credentials: {str(e)}")
        raise

def get_db_connection():
    """Create a database connection"""
    credentials = get_database_credentials()
    
    return psycopg2.connect(
        host=os.environ['DATABASE_ENDPOINT'],
        database=os.environ['DATABASE_NAME'],
        user=credentials['username'],
        password=credentials['password'],
        cursor_factory=RealDictCursor
    )

"""
There is an error in this function due to the timestamp handling. See this log in cloudwatch to illustrate:

<logs>
[INFO]	2025-07-21T15:13:31.632Z	74e3524d-748c-513c-8521-32b52fcefe3c	Processing message: 
{
    "id": "4f4dca0e-c6bd-4735-9ef8-24b1a10cfe0a",
    "title": "Inkbound 2",
    "genre": "Action",
    "rating": 9,
    "year": 2025,
    "created_at": "21/Jul/2025:15:11:36  0000"
}

[ERROR]	2025-07-21T15:13:31.775Z	74e3524d-748c-513c-8521-32b52fcefe3c	Error inserting movie: invalid input syntax for type timestamp: "21/Jul/2025:15:11:36  0000"
<logs>

As you can see, when a request from the SQS queue is processed, the `created_at` field is in a format that PostgreSQL does not recognize as a valid timestamp.

This is an example of a request sent as seen in the browser network tab POST /v1/api/movies {"title":"The Invincibles","genre":"Action","rating":9,"year":2005} ... note, no 'created_at'

And here is what was put in the SQS queue... I took this right from the AWS console:

{
  "id": "2e70745a-e43f-43d8-8748-9f4aca75eac9",
  "title": "The Invincibles",
  "genre": "Action",
  "rating": 9,
  "year": 2005,
  "created_at": "21/Jul/2025:15:30:48  0000"  // This is the problematic field
}
"""
def insert_movie(movie_data):
    """Insert a movie into the database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert movie with explicit ID
        insert_query = """
            INSERT INTO movies (id, title, genre, rating, year, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id;
        """
        
        cursor.execute(insert_query, (
            movie_data['id'],
            movie_data['title'],
            movie_data['genre'],
            movie_data['rating'],
            movie_data['year'],
            movie_data['created_at'],
            movie_data['created_at']  # Use created_at for both timestamps
        ))
        
        result = cursor.fetchone()
        conn.commit()
        
        if result:
            logger.info(f"Successfully inserted movie: {movie_data['title']} (ID: {movie_data['id']})")
            return True
        else:
            logger.warning(f"Movie already exists: {movie_data['id']}")
            return False
            
    except Exception as e:
        logger.error(f"Error inserting movie: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def handler(event, context):
    """Main Lambda handler for SQS events"""
    logger.info(f"Received SQS event with {len(event['Records'])} records")
    
    processed_count = 0
    error_count = 0
    
    # Process each SQS message
    for record in event['Records']:
        try:
            # Parse the message body
            message_body = json.loads(record['body'])
            logger.info(f"Processing message: {json.dumps(message_body)}")
            
            # Extract movie data based on message structure
            if isinstance(message_body, dict) and 'movie' in message_body:
                # Message contains action and movie
                movie_data = message_body['movie']
            else:
                # Message is the movie data directly
                movie_data = message_body
            
            # Insert movie into database
            if insert_movie(movie_data):
                processed_count += 1
            else:
                # Movie already existed, but not an error
                processed_count += 1
                
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            error_count += 1
            # In production, you might want to send failed messages to a DLQ
            # For now, we'll continue processing other messages
    
    logger.info(f"Processing complete. Processed: {processed_count}, Errors: {error_count}")
    
    # If any errors occurred, raise an exception to trigger retry
    if error_count > 0:
        raise Exception(f"Failed to process {error_count} messages")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_count,
            'total': len(event['Records'])
        })
    }

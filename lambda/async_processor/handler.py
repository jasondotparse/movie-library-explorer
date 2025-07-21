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

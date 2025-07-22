import json
import os
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

INSERT_MOVIE_QUERY = """
    INSERT INTO movies (id, title, genre, rating, year, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT ON CONSTRAINT unique_movie_combination DO NOTHING
    RETURNING id;
"""

def get_db_connection():
    secret = json.loads(boto3.client('secretsmanager').get_secret_value(
        SecretId=os.environ['DATABASE_SECRET_ARN'])['SecretString'])
    return psycopg2.connect(
        host=os.environ['DATABASE_ENDPOINT'],
        database=os.environ['DATABASE_NAME'],
        user=secret['username'],
        password=secret['password'],
        cursor_factory=RealDictCursor
    )

def insert_movie_into_db(movie_data):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(INSERT_MOVIE_QUERY, (movie_data['id'], movie_data['title'], movie_data['genre'], 
                  movie_data['rating'], movie_data['year'], now, now))
            
            result = cursor.fetchone()
            print(f"{'Inserted' if result else 'Exists'}: {movie_data['title']}")
            return bool(result)

def handler(event, _):
    """
    Handle a batch of SQS messages to insert movies into the PostgreSQL database in RDS.
    If the movie already exists, it will skip the insertion.
    """
    print(f"Event triggered by SQS. Processing {len(event['Records'])} records...")
    processed = error_count = 0
    
    for record in event['Records']:
        try:
            body = json.loads(record['body'])
            movie_data = body['movie'] if 'movie' in body else body
            insert_movie_into_db(movie_data)
            processed += 1
        except Exception as e:
            print(f"Error processing record: {e}")
            error_count += 1
    
    print(f"Complete: {processed} processed, {error_count} errors")
    if error_count:
        raise Exception(f"Failed to process {error_count} messages")
    return {'statusCode': 200}

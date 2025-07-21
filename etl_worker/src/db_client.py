"""
PostgreSQL database client for storing movie metadata.
"""

import json
import logging
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class DBClient:
    """Client for interacting with PostgreSQL database."""
    
    def __init__(self, db_secret_arn: str, aws_region: str):
        """
        Initialize the database client.
        
        Args:
            db_secret_arn: ARN of the database secret in AWS Secrets Manager
            aws_region: AWS region where the secret is stored
        """
        self.db_secret_arn = db_secret_arn
        self.aws_region = aws_region
        self.connection = None
        self.connection_params = self._get_database_credentials()
        
    def _get_database_credentials(self) -> Dict[str, str]:
        """Retrieve database credentials from AWS Secrets Manager."""
        try:
            logger.info(f"Retrieving database credentials from AWS Secrets Manager")
            
            # Create a Secrets Manager client
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=self.aws_region
            )
            
            # Retrieve the secret
            response = client.get_secret_value(SecretId=self.db_secret_arn)
            secret = json.loads(response['SecretString'])
            
            logger.info("Successfully retrieved database credentials")
            
            return {
                'host': secret['host'],
                'port': secret['port'],
                'database': secret['dbname'],
                'user': secret['username'],
                'password': secret['password']
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve database credentials: {str(e)}")
            raise
        
    def connect(self):
        """Establish connection to the database."""
        try:
            self.connection = psycopg2.connect(**self.connection_params)
            self.connection.autocommit = False
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from database")
    
    def insert_movie(self, movie_data: Dict[str, Any]) -> Optional[str]:
        """
        Insert a single movie into the database, skipping duplicates.
        
        Args:
            movie_data: Dictionary with movie information (title, genre, rating, year)
            
        Returns:
            The UUID of the inserted movie, or None if duplicate was skipped
        """
        try:
            cursor = self.connection.cursor()
            
            # Insert movie using ON CONFLICT to skip duplicates
            insert_query = """
                INSERT INTO movies (title, genre, rating, year)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (title, genre, rating, year) 
                DO NOTHING
                RETURNING id::text;
            """
            
            cursor.execute(insert_query, (
                movie_data.get('title'),
                movie_data.get('genre'),
                movie_data.get('rating'),
                movie_data.get('year')
            ))
            
            result = cursor.fetchone()
            movie_id = result[0] if result else None
            
            self.connection.commit()
            cursor.close()
            
            if not movie_id:
                logger.info(f"Skipped duplicate movie: {movie_data.get('title')} ({movie_data.get('genre')}, {movie_data.get('year')}, rating {movie_data.get('rating')})")
            
            return movie_id
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to insert movie {movie_data.get('title', 'unknown')}: {str(e)}")
            return None
    
    def bulk_insert_movies(self, movies: List[Dict[str, Any]]) -> int:
        """
        Bulk insert multiple movies into the database.
        
        Args:
            movies: List of dictionaries with movie information
            
        Returns:
            Number of successfully inserted/updated movies
        """
        if not movies:
            return 0
            
        try:
            cursor = self.connection.cursor()
            
            # Prepare data for bulk insert
            values = []
            for movie in movies:
                values.append((
                    movie.get('title'),
                    movie.get('genre'),
                    movie.get('rating'),
                    movie.get('year')
                ))
            
            # Use execute_batch for better performance
            insert_query = """
                INSERT INTO movies (title, genre, rating, year)
                VALUES (%s, %s, %s, %s);
            """
            
            execute_batch(cursor, insert_query, values, page_size=100)
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"Successfully inserted/updated {len(movies)} movies")
            return len(movies)
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to bulk insert movies: {str(e)}")
            return 0
    
    def check_table_exists(self) -> bool:
        """Check if the movies table exists."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'movies'
                );
            """)
            exists = cursor.fetchone()[0]
            cursor.close()
            return exists
        except Exception as e:
            logger.error(f"Failed to check if table exists: {str(e)}")
            return False
    
    def get_movie_count(self) -> int:
        """Get the total number of movies in the database."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM movies;")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            logger.error(f"Failed to get movie count: {str(e)}")
            return 0

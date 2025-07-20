"""
PostgreSQL database client for storing movie metadata.
"""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class DBClient:
    """Client for interacting with PostgreSQL database."""
    
    def __init__(self, connection_params: dict):
        """
        Initialize the database client.
        
        Args:
            connection_params: Dictionary with database connection parameters
        """
        self.connection_params = connection_params
        self.connection = None
        
    def connect(self):
        """Establish connection to the database."""
        try:
            self.connection = psycopg2.connect(**self.connection_params)
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from database")
    
    # TODO: Implement movie insertion and query methods
    # def insert_movie(self, movie_data: dict):
    # def get_movie_by_id(self, movie_id: str):
    # def bulk_insert_movies(self, movies: list):

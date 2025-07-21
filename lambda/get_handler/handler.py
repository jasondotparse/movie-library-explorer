import json
import os
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal
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

def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    """Main Lambda handler for GET requests"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract HTTP method and path
    http_method = event.get('httpMethod', '')
    path = event.get('path', '')
    query_params = event.get('queryStringParameters', {}) or {}
    
    # Route to appropriate handler
    try:
        if path == '/api/movies/search' and http_method == 'GET':
            return handle_search(query_params)
        elif path == '/api/dashboard' and http_method == 'GET':
            return handle_dashboard()
        elif path == '/api/movies/filter' and http_method == 'GET':
            return handle_filter(query_params)
        elif path == '/api/movies/top-rated' and http_method == 'GET':
            return handle_top_rated(query_params)
        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': {'code': 'NOT_FOUND', 'message': 'Endpoint not found'}})
            }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'An internal error occurred',
                    'details': str(e) if context.function_name.endswith('-dev') else None
                }
            })
        }

def handle_search(query_params):
    """Handle movie search by title"""
    title = query_params.get('title', '').strip()
    
    if not title:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Title parameter is required'
                }
            })
        }
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use ILIKE for case-insensitive partial matching
        query = """
            SELECT id, title, genre, rating, year, created_at
            FROM movies
            WHERE title ILIKE %s
            ORDER BY title
        """
        cursor.execute(query, (f'%{title}%',))
        movies = cursor.fetchall()
        
        # Convert to list of dicts and handle Decimal
        movies_list = []
        for movie in movies:
            movie_dict = dict(movie)
            movie_dict['created_at'] = movie_dict['created_at'].isoformat() if movie_dict['created_at'] else None
            movies_list.append(movie_dict)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'movies': movies_list}, default=decimal_to_float)
        }
        
    finally:
        if conn:
            conn.close()

def handle_dashboard():
    """Handle dashboard statistics request"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total movie count
        cursor.execute("SELECT COUNT(*) as count FROM movies")
        total_movies = cursor.fetchone()['count']
        
        # Get average rating
        cursor.execute("SELECT AVG(rating) as avg_rating FROM movies")
        avg_rating_result = cursor.fetchone()['avg_rating']
        avg_rating = float(avg_rating_result) if avg_rating_result else 0
        
        # Get top genres by count
        cursor.execute("""
            SELECT genre, COUNT(*) as count
            FROM movies
            GROUP BY genre
            ORDER BY count DESC, genre
            LIMIT 10
        """)
        top_genres = [{'genre': row['genre'], 'count': row['count']} for row in cursor.fetchall()]
        
        # Get movies by year
        cursor.execute("""
            SELECT year, COUNT(*) as count
            FROM movies
            GROUP BY year
            ORDER BY year DESC
            LIMIT 20
        """)
        movies_by_year = [{'year': row['year'], 'count': row['count']} for row in cursor.fetchall()]
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'totalMovies': total_movies,
                'averageRating': round(avg_rating, 1),
                'topGenres': top_genres,
                'moviesByYear': movies_by_year
            })
        }
        
    finally:
        if conn:
            conn.close()

def handle_filter(query_params):
    """Handle filtered movie search"""
    # Extract filter parameters
    genres = query_params.getlist('genre') if hasattr(query_params, 'getlist') else query_params.get('genre', [])
    if isinstance(genres, str):
        genres = [genres]
    
    min_rating = query_params.get('minRating', '')
    year = query_params.get('year', '')
    
    # Build dynamic query
    query_parts = ["SELECT id, title, genre, rating, year, created_at FROM movies WHERE 1=1"]
    params = []
    
    if genres:
        placeholders = ','.join(['%s'] * len(genres))
        query_parts.append(f"AND genre IN ({placeholders})")
        params.extend(genres)
    
    if min_rating:
        try:
            min_rating_float = float(min_rating)
            query_parts.append("AND rating >= %s")
            params.append(min_rating_float)
        except ValueError:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Invalid minRating value'
                    }
                })
            }
    
    if year:
        try:
            year_int = int(year)
            query_parts.append("AND year = %s")
            params.append(year_int)
        except ValueError:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Invalid year value'
                    }
                })
            }
    
    query_parts.append("ORDER BY rating DESC, title")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = ' '.join(query_parts)
        cursor.execute(query, params)
        movies = cursor.fetchall()
        
        # Convert to list of dicts
        movies_list = []
        for movie in movies:
            movie_dict = dict(movie)
            movie_dict['created_at'] = movie_dict['created_at'].isoformat() if movie_dict['created_at'] else None
            movies_list.append(movie_dict)
        
        # Build filter summary
        filters = {}
        if genres:
            filters['genres'] = genres
        if min_rating:
            filters['minRating'] = float(min_rating)
        if year:
            filters['year'] = int(year)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'movies': movies_list,
                'totalCount': len(movies_list),
                'filters': filters
            }, default=decimal_to_float)
        }
        
    finally:
        if conn:
            conn.close()

def handle_top_rated(query_params):
    """Handle top-rated movies with pagination"""
    # Extract pagination parameters
    start = int(query_params.get('start', 0))
    limit = int(query_params.get('limit', 10))
    
    # Validate pagination parameters
    if start < 0 or limit < 1 or limit > 100:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Invalid pagination parameters'
                }
            })
        }
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as count FROM movies")
        total_count = cursor.fetchone()['count']
        
        # Get paginated top-rated movies
        query = """
            SELECT id, title, genre, rating, year
            FROM movies
            ORDER BY rating DESC, title
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (limit, start))
        movies = cursor.fetchall()
        
        # Convert to list of dicts
        movies_list = []
        for movie in movies:
            movie_dict = dict(movie)
            movies_list.append(movie_dict)
        
        # Calculate if there are more results
        has_more = (start + limit) < total_count
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'movies': movies_list,
                'pagination': {
                    'start': start,
                    'limit': limit,
                    'total': total_count,
                    'hasMore': has_more
                }
            }, default=decimal_to_float)
        }
        
    finally:
        if conn:
            conn.close()

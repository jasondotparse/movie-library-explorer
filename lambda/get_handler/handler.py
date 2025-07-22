import json
import os
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal

# SQL Queries
SEARCH_QUERY = """
    SELECT id, title, genre, rating, year, created_at
    FROM movies
    WHERE title ILIKE %s
    ORDER BY title
"""

DASHBOARD_QUERIES = {
    'count': "SELECT COUNT(*) as count FROM movies",
    'avg_rating': "SELECT AVG(rating) as avg_rating FROM movies",
    'top_genres': """
        SELECT genre, COUNT(*) as count
        FROM movies
        GROUP BY genre
        ORDER BY count DESC, genre
        LIMIT 10
    """,
    'movies_by_year': """
        SELECT year, COUNT(*) as count
        FROM movies
        GROUP BY year
        ORDER BY year DESC
        LIMIT 20
    """
}

FILTER_BASE_QUERY = "SELECT id, title, genre, rating, year, created_at FROM movies WHERE 1=1"
FILTER_ORDER = " ORDER BY rating DESC, title"

TOP_RATED_COUNT_QUERY = "SELECT COUNT(*) as count FROM movies"
TOP_RATED_QUERY = """
    SELECT id, title, genre, rating, year
    FROM movies
    ORDER BY rating DESC, title
    LIMIT %s OFFSET %s
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

def decimal_to_float(obj):
    return float(obj) if isinstance(obj, Decimal) else obj

def handler(event, context):
    """Main Lambda handler for GET requests. Invoked by API Gateway"""
    print(f"Processing {event.get('httpMethod')} {event.get('path')}")
    
    path = event.get('path', '')
    query_params = event.get('queryStringParameters', {}) or {}
    
    try:
        if path == '/api/movies/search':
            return handle_search(query_params)
        elif path == '/api/dashboard':
            return handle_dashboard()
        elif path == '/api/movies/filter':
            return handle_filter(query_params)
        elif path == '/api/movies/top-rated':
            return handle_top_rated(query_params)
        else:
            return error_response(404, 'NOT_FOUND', 'Endpoint not found')
    except Exception as e:
        print(f"Error: {e}")
        return error_response(500, 'INTERNAL_ERROR', 'An internal error occurred')

def error_response(status_code, error_code, message):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'error': {'code': error_code, 'message': message}})
    }

def success_response(data):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(data, default=decimal_to_float)
    }

def handle_search(query_params):
    """Handle movie search by title"""
    title = query_params.get('title', '').strip()
    if not title:
        return error_response(400, 'VALIDATION_ERROR', 'Title parameter is required')
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(SEARCH_QUERY, (f'%{title}%',))
            movies = [
                {**dict(movie), 'created_at': movie['created_at'].isoformat() if movie['created_at'] else None}
                for movie in cursor.fetchall()
            ]
            return success_response({'movies': movies})

def handle_dashboard():
    """Handle dashboard statistics request"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(DASHBOARD_QUERIES['count'])
            total_movies = cursor.fetchone()['count']
            
            cursor.execute(DASHBOARD_QUERIES['avg_rating'])
            avg_rating = cursor.fetchone()['avg_rating']
            avg_rating = float(avg_rating) if avg_rating else 0
            
            cursor.execute(DASHBOARD_QUERIES['top_genres'])
            top_genres = [{'genre': row['genre'], 'count': row['count']} for row in cursor.fetchall()]
            
            cursor.execute(DASHBOARD_QUERIES['movies_by_year'])
            movies_by_year = [{'year': row['year'], 'count': row['count']} for row in cursor.fetchall()]
            
            return success_response({
                'totalMovies': total_movies,
                'averageRating': round(avg_rating, 1),
                'topGenres': top_genres,
                'moviesByYear': movies_by_year
            })

def handle_filter(query_params):
    """Handle filtered movie search"""
    genres = query_params.getlist('genre') if hasattr(query_params, 'getlist') else query_params.get('genre', [])
    if isinstance(genres, str):
        genres = [genres]
    
    min_rating = query_params.get('minRating', '')
    year = query_params.get('year', '')
    
    # Build dynamic query
    query_parts = [FILTER_BASE_QUERY]
    params = []
    
    if genres:
        placeholders = ','.join(['%s'] * len(genres))
        query_parts.append(f"AND genre IN ({placeholders})")
        params.extend(genres)
    
    if min_rating:
        try:
            query_parts.append("AND rating >= %s")
            params.append(float(min_rating))
        except ValueError:
            return error_response(400, 'VALIDATION_ERROR', 'Invalid minRating value')
    
    if year:
        try:
            query_parts.append("AND year = %s")
            params.append(int(year))
        except ValueError:
            return error_response(400, 'VALIDATION_ERROR', 'Invalid year value')
    
    query_parts.append(FILTER_ORDER)
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(' '.join(query_parts), params)
            movies = [
                {**dict(movie), 'created_at': movie['created_at'].isoformat() if movie['created_at'] else None}
                for movie in cursor.fetchall()
            ]
            
            filters = {}
            if genres:
                filters['genres'] = genres
            if min_rating:
                filters['minRating'] = float(min_rating)
            if year:
                filters['year'] = int(year)
            
            return success_response({
                'movies': movies,
                'totalCount': len(movies),
                'filters': filters
            })

def handle_top_rated(query_params):
    """Handle top-rated movies with pagination"""
    start = int(query_params.get('start', 0))
    limit = int(query_params.get('limit', 10))
    
    if start < 0 or limit < 1 or limit > 100:
        return error_response(400, 'VALIDATION_ERROR', 'Invalid pagination parameters')
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(TOP_RATED_COUNT_QUERY)
            total_count = cursor.fetchone()['count']
            
            cursor.execute(TOP_RATED_QUERY, (limit, start))
            movies = [dict(movie) for movie in cursor.fetchall()]
            
            return success_response({
                'movies': movies,
                'pagination': {
                    'start': start,
                    'limit': limit,
                    'total': total_count,
                    'hasMore': (start + limit) < total_count
                }
            })

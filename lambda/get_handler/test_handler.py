import pytest
from unittest.mock import patch, MagicMock, call
import json
from handler import handler, handle_search, handle_dashboard, handle_filter, handle_top_rated


class TestGetHandler:
    
    @patch('handler.get_db_connection')
    def test_search_executes_correct_query(self, mock_get_db):
        """Test that search executes the correct ILIKE query with proper parameters"""
        # Setup mock for context manager
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.fetchall.return_value = [
            {'id': '123', 'title': 'Test Movie', 'genre': 'Action', 'rating': 8.5, 'year': 2020, 'created_at': None}
        ]
        mock_get_db.return_value = mock_conn
        
        # Execute
        query_params = {'title': 'test'}
        response = handle_search(query_params)
        
        # Verify query execution (using the constant)
        from handler import SEARCH_QUERY
        mock_cursor.execute.assert_called_once_with(SEARCH_QUERY, ('%test%',))
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'movies' in body
        assert len(body['movies']) == 1
    
    @patch('handler.get_db_connection')
    def test_dashboard_executes_all_required_queries(self, mock_get_db):
        """Test that dashboard executes all 4 required queries in correct order"""
        # Setup mock for context manager
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_get_db.return_value = mock_conn
        
        # Mock query results
        mock_cursor.fetchone.side_effect = [
            {'count': 100},  # total movies
            {'avg_rating': 7.5}  # average rating
        ]
        mock_cursor.fetchall.side_effect = [
            [{'genre': 'Action', 'count': 25}, {'genre': 'Comedy', 'count': 20}],  # top genres
            [{'year': 2023, 'count': 15}, {'year': 2022, 'count': 12}]  # movies by year
        ]
        
        # Execute
        response = handle_dashboard()
        
        # Verify all queries were executed using constants
        from handler import DASHBOARD_QUERIES
        expected_calls = [
            call(DASHBOARD_QUERIES['count']),
            call(DASHBOARD_QUERIES['avg_rating']),
            call(DASHBOARD_QUERIES['top_genres']),
            call(DASHBOARD_QUERIES['movies_by_year'])
        ]
        
        mock_cursor.execute.assert_has_calls(expected_calls)
        assert mock_cursor.execute.call_count == 4
        
        # Verify response structure
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'totalMovies' in body
        assert 'averageRating' in body
        assert 'topGenres' in body
        assert 'moviesByYear' in body

    @patch('handler.get_db_connection')
    def test_filter_builds_query_with_all_filters(self, mock_get_db):
        """Test that filter builds correct dynamic query with all parameters"""
        # Setup mock for context manager
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_get_db.return_value = mock_conn
        
        # Execute with all filters (simulating multiple genres)
        query_params = {
            'genre': ['Action', 'Comedy'],
            'minRating': '7.0',
            'year': '2022'
        }
        response = handle_filter(query_params)
        
        # Verify query construction (note the extra space before ORDER BY due to how query parts are joined)
        expected_query = "SELECT id, title, genre, rating, year, created_at FROM movies WHERE 1=1 AND genre IN (%s,%s) AND rating >= %s AND year = %s  ORDER BY rating DESC, title"
        expected_params = ['Action', 'Comedy', 7.0, 2022]
        
        mock_cursor.execute.assert_called_once_with(expected_query, expected_params)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'filters' in body
        assert body['filters']['genres'] == ['Action', 'Comedy']
        assert body['filters']['minRating'] == 7.0
        assert body['filters']['year'] == 2022

    @patch('handler.get_db_connection')
    def test_top_rated_executes_pagination_queries(self, mock_get_db):
        """Test that top-rated executes count and pagination queries"""
        # Setup mock for context manager
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_get_db.return_value = mock_conn
        
        # Mock results
        mock_cursor.fetchone.return_value = {'count': 50}  # total count
        mock_cursor.fetchall.return_value = [
            {'id': '1', 'title': 'Top Movie', 'genre': 'Action', 'rating': 9.5, 'year': 2023}
        ]
        
        # Execute with pagination
        query_params = {'start': '10', 'limit': '5'}
        response = handle_top_rated(query_params)
        
        # Verify both queries were executed using constants
        from handler import TOP_RATED_COUNT_QUERY, TOP_RATED_QUERY
        expected_calls = [
            call(TOP_RATED_COUNT_QUERY),
            call(TOP_RATED_QUERY, (5, 10))
        ]
        
        mock_cursor.execute.assert_has_calls(expected_calls)
        assert mock_cursor.execute.call_count == 2
        
        # Verify pagination response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'pagination' in body
        assert body['pagination']['start'] == 10
        assert body['pagination']['limit'] == 5
        assert body['pagination']['total'] == 50
        assert body['pagination']['hasMore'] is True  # (10 + 5) < 50

    def test_search_validation_missing_title(self):
        """Test search returns 400 for missing title parameter"""
        response = handle_search({})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'Title parameter is required' in body['error']['message']

    def test_filter_validation_invalid_rating(self):
        """Test filter returns 400 for invalid rating"""
        query_params = {'minRating': 'invalid'}
        response = handle_filter(query_params)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'Invalid minRating value' in body['error']['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

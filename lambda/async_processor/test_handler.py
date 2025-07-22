import pytest
from unittest.mock import patch, MagicMock
import json
from handler import handler, insert_movie_into_db


class TestAsyncProcessor:
    
    @patch('handler.get_db_connection')
    def test_insert_movie_executes_correct_query(self, mock_get_db):
        """Test that insert_movie executes the correct INSERT query with proper parameters"""
        # Setup mock for context manager
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.fetchone.return_value = {'id': 'test-uuid'}
        mock_get_db.return_value = mock_conn
        
        # Test data
        movie_data = {
            'id': 'test-uuid',
            'title': 'Test Movie',
            'genre': 'Action',
            'rating': 8.5,
            'year': 2023
        }
        
        # Execute
        result = insert_movie_into_db(movie_data)
        
        # Verify query execution using the constant
        from handler import INSERT_MOVIE_QUERY
        args = mock_cursor.execute.call_args[0]
        assert args[0] == INSERT_MOVIE_QUERY
        
        # Verify parameters (except timestamps which are dynamic)
        params = args[1]
        assert params[0] == 'test-uuid'  # id
        assert params[1] == 'Test Movie'  # title
        assert params[2] == 'Action'  # genre
        assert params[3] == 8.5  # rating
        assert params[4] == 2023  # year
        # params[5] and params[6] are timestamps, we'll skip exact validation
        
        # Verify return value
        assert result is True
    
    @patch('handler.get_db_connection')
    def test_insert_movie_handles_duplicate(self, mock_get_db):
        """Test that insert_movie handles duplicate movies correctly"""
        # Setup mock for context manager - no result indicates duplicate
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.fetchone.return_value = None  # No result = duplicate skipped
        mock_get_db.return_value = mock_conn
        
        # Test data
        movie_data = {
            'id': 'test-uuid',
            'title': 'Duplicate Movie',
            'genre': 'Comedy',
            'rating': 7.0,
            'year': 2022
        }
        
        # Execute
        result = insert_movie_into_db(movie_data)
        
        # Verify return value for duplicate
        assert result is False
    
    @patch('handler.insert_movie_into_db')
    def test_handler_processes_sqs_records(self, mock_insert):
        """Test that handler processes SQS records correctly"""
        mock_insert.return_value = True
        
        # Create mock SQS event
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'id': 'movie-1',
                        'title': 'Movie 1',
                        'genre': 'Action',
                        'rating': 8.0,
                        'year': 2023
                    })
                },
                {
                    'body': json.dumps({
                        'movie': {
                            'id': 'movie-2',
                            'title': 'Movie 2',
                            'genre': 'Comedy',
                            'rating': 7.5,
                            'year': 2022
                        }
                    })
                }
            ]
        }
        
        # Execute
        response = handler(event, None)
        
        # Verify both records were processed
        assert mock_insert.call_count == 2
        
        # Verify response
        assert response['statusCode'] == 200
    
    @patch('handler.insert_movie_into_db')
    def test_handler_handles_errors(self, mock_insert):
        """Test that handler handles errors correctly"""
        # First call succeeds, second fails
        mock_insert.side_effect = [True, Exception("Database error")]
        
        # Create mock SQS event with 2 records
        event = {
            'Records': [
                {'body': json.dumps({'id': '1', 'title': 'Good Movie', 'genre': 'Action', 'rating': 8.0, 'year': 2023})},
                {'body': json.dumps({'id': '2', 'title': 'Bad Movie', 'genre': 'Drama', 'rating': 7.0, 'year': 2022})}
            ]
        }
        
        # Execute - should raise exception due to error
        with pytest.raises(Exception) as exc_info:
            handler(event, None)
        
        assert "Failed to process 1 messages" in str(exc_info.value)
    
    @patch('handler.insert_movie_into_db')
    def test_handler_processes_different_message_formats(self, mock_insert):
        """Test handler processes both direct and nested message formats"""
        mock_insert.return_value = True
        
        # Test both message formats
        event = {
            'Records': [
                # Direct format
                {'body': json.dumps({
                    'id': 'direct-movie',
                    'title': 'Direct Movie',
                    'genre': 'Action',
                    'rating': 8.0,
                    'year': 2023
                })},
                # Nested format
                {'body': json.dumps({
                    'movie': {
                        'id': 'nested-movie',
                        'title': 'Nested Movie', 
                        'genre': 'Comedy',
                        'rating': 7.0,
                        'year': 2022
                    }
                })}
            ]
        }
        
        # Execute
        response = handler(event, None)
        
        # Verify both formats were processed
        assert mock_insert.call_count == 2
        
        # Check the actual movie data passed to insert_movie_into_db
        calls = mock_insert.call_args_list
        
        # First call - direct format
        assert calls[0][0][0]['title'] == 'Direct Movie'
        
        # Second call - nested format
        assert calls[1][0][0]['title'] == 'Nested Movie'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

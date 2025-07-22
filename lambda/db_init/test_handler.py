import pytest
from unittest.mock import patch, MagicMock, call
import json
from handler import lambda_handler, initialize_database


class TestDbInit:
    
    @patch('boto3.client')
    @patch('psycopg2.connect')
    def test_initialize_database_executes_all_queries(self, mock_connect, mock_boto3):
        """Test that initialize_database executes all required SQL statements in correct order"""
        # Setup mocks for Secrets Manager
        mock_secrets_client = MagicMock()
        mock_boto3.return_value = mock_secrets_client
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'host': 'localhost',
                'port': 5432,
                'dbname': 'testdb',
                'username': 'user',
                'password': 'pass'
            })
        }
        
        # Setup database mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ('column1', 'VARCHAR', 'NO', None),
            ('column2', 'INTEGER', 'YES', 'DEFAULT')
        ]
        
        # Execute
        initialize_database('test-secret-arn')
        
        # Verify all SQL queries were executed in order
        from handler import (ENABLE_UUID_EXTENSION, CREATE_MOVIES_TABLE, 
                           CREATE_INDEXES, ADD_UNIQUE_CONSTRAINT, 
                           VERIFY_TABLE_SCHEMA, CHECK_INDEXES)
        
        expected_calls = [
            call(ENABLE_UUID_EXTENSION),
            call(CREATE_MOVIES_TABLE),
            call(CREATE_INDEXES[0]),  # idx_movies_title
            call(CREATE_INDEXES[1]),  # idx_movies_genre  
            call(CREATE_INDEXES[2]),  # idx_movies_year
            call(CREATE_INDEXES[3]),  # idx_movies_rating
            call(ADD_UNIQUE_CONSTRAINT),
            call(VERIFY_TABLE_SCHEMA),
            call(CHECK_INDEXES)
        ]
        
        mock_cursor.execute.assert_has_calls(expected_calls)
        assert mock_cursor.execute.call_count == 9
        
        # Verify connection management
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('boto3.client')
    @patch('psycopg2.connect')
    def test_initialize_database_handles_errors(self, mock_connect, mock_boto3):
        """Test that initialize_database handles database errors correctly"""
        # Setup mocks for Secrets Manager
        mock_secrets_client = MagicMock()
        mock_boto3.return_value = mock_secrets_client
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'host': 'localhost',
                'port': 5432,
                'dbname': 'testdb',
                'username': 'user',
                'password': 'pass'
            })
        }
        
        # Setup database mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Execute and verify exception is raised
        with pytest.raises(Exception) as exc_info:
            initialize_database('test-secret-arn')
        
        assert "Database error" in str(exc_info.value)
        
        # Verify rollback was called
        mock_conn.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('handler.initialize_database')
    @patch('handler.send')
    def test_lambda_handler_create_request(self, mock_send, mock_initialize):
        """Test lambda_handler processes CREATE requests correctly"""
        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'DatabaseSecretArn': 'arn:aws:secretsmanager:us-west-1:123456789:secret:test'
            },
            'ResponseURL': 'https://test-url.com',
            'StackId': 'test-stack',
            'RequestId': 'test-request',
            'LogicalResourceId': 'test-resource'
        }
        context = MagicMock()
        context.log_stream_name = 'test-stream'
        
        # Execute
        lambda_handler(event, context)
        
        # Verify database initialization was called
        mock_initialize.assert_called_once_with('arn:aws:secretsmanager:us-west-1:123456789:secret:test')
        
        # Verify SUCCESS response was sent
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert args[2] == 'SUCCESS'  # responseStatus
    
    @patch('handler.initialize_database')
    @patch('handler.send')
    def test_lambda_handler_update_request(self, mock_send, mock_initialize):
        """Test lambda_handler processes UPDATE requests correctly"""
        event = {
            'RequestType': 'Update',
            'ResourceProperties': {
                'DatabaseSecretArn': 'arn:aws:secretsmanager:us-west-1:123456789:secret:test'
            },
            'ResponseURL': 'https://test-url.com',
            'StackId': 'test-stack',
            'RequestId': 'test-request',
            'LogicalResourceId': 'test-resource'
        }
        context = MagicMock()
        context.log_stream_name = 'test-stream'
        
        # Execute
        lambda_handler(event, context)
        
        # Verify database initialization was called
        mock_initialize.assert_called_once_with('arn:aws:secretsmanager:us-west-1:123456789:secret:test')
        
        # Verify SUCCESS response was sent
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert args[2] == 'SUCCESS'  # responseStatus
    
    @patch('handler.initialize_database')
    @patch('handler.send')
    def test_lambda_handler_delete_request(self, mock_send, mock_initialize):
        """Test lambda_handler processes DELETE requests correctly (no database operations)"""
        event = {
            'RequestType': 'Delete',
            'ResourceProperties': {
                'DatabaseSecretArn': 'arn:aws:secretsmanager:us-west-1:123456789:secret:test'
            },
            'ResponseURL': 'https://test-url.com',
            'StackId': 'test-stack',
            'RequestId': 'test-request',
            'LogicalResourceId': 'test-resource'
        }
        context = MagicMock()
        context.log_stream_name = 'test-stream'
        
        # Execute
        lambda_handler(event, context)
        
        # Verify database initialization was NOT called for DELETE
        mock_initialize.assert_not_called()
        
        # Verify SUCCESS response was sent
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert args[2] == 'SUCCESS'  # responseStatus
    
    @patch('handler.initialize_database')
    @patch('handler.send')
    def test_lambda_handler_missing_secret_arn(self, mock_send, mock_initialize):
        """Test lambda_handler handles missing DatabaseSecretArn"""
        event = {
            'RequestType': 'Create',
            'ResourceProperties': {},  # Missing DatabaseSecretArn
            'ResponseURL': 'https://test-url.com',
            'StackId': 'test-stack',
            'RequestId': 'test-request',
            'LogicalResourceId': 'test-resource'
        }
        context = MagicMock()
        context.log_stream_name = 'test-stream'
        
        # Execute
        lambda_handler(event, context)
        
        # Verify database initialization was NOT called
        mock_initialize.assert_not_called()
        
        # Verify SUCCESS response was still sent (for debugging)
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert args[2] == 'SUCCESS'  # responseStatus
    
    @patch('handler.initialize_database')
    @patch('handler.send')
    def test_lambda_handler_handles_initialization_error(self, mock_send, mock_initialize):
        """Test lambda_handler handles database initialization errors gracefully"""
        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'DatabaseSecretArn': 'arn:aws:secretsmanager:us-west-1:123456789:secret:test'
            },
            'ResponseURL': 'https://test-url.com',
            'StackId': 'test-stack',
            'RequestId': 'test-request',
            'LogicalResourceId': 'test-resource'
        }
        context = MagicMock()
        context.log_stream_name = 'test-stream'
        
        # Setup initialization to fail
        mock_initialize.side_effect = Exception("Initialization failed")
        
        # Execute
        lambda_handler(event, context)
        
        # Verify SUCCESS response was still sent (for debugging)
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert args[2] == 'SUCCESS'  # responseStatus


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

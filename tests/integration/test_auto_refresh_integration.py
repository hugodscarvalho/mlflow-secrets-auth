"""Integration tests for auto-refresh functionality."""

import json
import os
from unittest.mock import Mock, patch

import requests

from mlflow_secrets_auth.providers.aws_secrets_manager import AWSSecretsManagerAuthProvider


class TestAutoRefreshIntegration:
    """Integration tests for auto-refresh functionality with real providers."""

    def setup_method(self):
        """Setup test environment."""
        # Clear any existing environment variables
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AWS_')):
                del os.environ[key]

        # Set required environment variables
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "aws-secrets-manager"
        os.environ["AWS_REGION"] = "us-west-2"
        os.environ["MLFLOW_AWS_SECRET_ID"] = "mlflow-auth-secret"

    @patch('boto3.client')
    @patch('requests.Session.send')
    def test_aws_provider_auto_refresh_on_401(self, mock_send, mock_boto_client):
        """Test complete auto-refresh flow with AWS provider on 401 response."""
        # Mock boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Track calls to get_secret_value
        call_count = 0

        def mock_get_secret_value(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call returns original token
                return {
                    'SecretString': json.dumps({
                        'token': 'original-token-123',
                    }),
                }
            # Subsequent calls return refreshed token
            return {
                'SecretString': json.dumps({
                    'token': 'refreshed-token-456',
                }),
            }

        mock_client.get_secret_value.side_effect = mock_get_secret_value

        provider = AWSSecretsManagerAuthProvider()
        auth = provider.get_auth()

        # Verify we got an auto-refresh auth wrapper
        from mlflow_secrets_auth.base import _AutoRefreshAuth
        assert isinstance(auth, _AutoRefreshAuth)

        # Create a mock request that will receive a 401
        mock_request = Mock(spec=requests.PreparedRequest)
        mock_request.headers = {}
        mock_request.hooks = {}
        mock_request.copy = Mock(return_value=Mock(spec=requests.PreparedRequest))
        mock_request.copy.return_value.headers = {}

        # Apply authentication to the request
        authenticated_request = auth(mock_request)

        # Verify the original token was applied
        assert "Authorization" in authenticated_request.headers
        assert authenticated_request.headers["Authorization"] == "Bearer original-token-123"

        # Simulate a 401 response
        mock_401_response = Mock(spec=requests.Response)
        mock_401_response.status_code = 401
        mock_401_response.request = mock_request

        # Mock the retry response (successful after refresh)
        mock_retry_response = Mock(spec=requests.Response)
        mock_retry_response.status_code = 200
        mock_send.return_value = mock_retry_response

        # Set up session connection for retry
        mock_session = Mock(spec=requests.Session)
        mock_session.send = mock_send
        mock_401_response.connection = mock_session

        # Trigger the response handler (this would normally be called by requests)
        response_handler = authenticated_request.hooks["response"][0]
        final_response = response_handler(mock_401_response)

        # Verify the flow:
        # 1. Original secret was fetched once for initial auth
        # 2. After 401, secret was fetched again for refresh
        assert call_count == 2

        # 3. The retry was sent with fresh credentials
        mock_send.assert_called_once()
        retry_request = mock_send.call_args[0][0]
        assert retry_request.headers["X-MLFSA-Retried"] == "true"
        assert retry_request.headers["Authorization"] == "Bearer refreshed-token-456"

        # 4. The successful retry response was returned
        assert final_response == mock_retry_response

    @patch('boto3.client')
    def test_aws_provider_auto_refresh_on_403(self, mock_boto_client):
        """Test auto-refresh flow with 403 response."""
        # Similar test but with 403 status code
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        call_count = 0

        def mock_get_secret_value(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                'SecretString': json.dumps({
                    'token': f'token-attempt-{call_count}',
                }),
            }

        mock_client.get_secret_value.side_effect = mock_get_secret_value

        provider = AWSSecretsManagerAuthProvider()
        auth = provider.get_auth()

        # Create mock request and apply auth
        mock_request = Mock(spec=requests.PreparedRequest)
        mock_request.headers = {}
        mock_request.hooks = {}
        mock_request.copy = Mock(return_value=Mock(spec=requests.PreparedRequest))
        mock_request.copy.return_value.headers = {}

        authenticated_request = auth(mock_request)

        # Simulate 403 response
        mock_403_response = Mock(spec=requests.Response)
        mock_403_response.status_code = 403
        mock_403_response.request = mock_request

        mock_retry_response = Mock(spec=requests.Response)
        mock_retry_response.status_code = 200

        mock_session = Mock(spec=requests.Session)
        mock_session.send.return_value = mock_retry_response
        mock_403_response.connection = mock_session

        # Trigger refresh
        response_handler = authenticated_request.hooks["response"][0]
        final_response = response_handler(mock_403_response)

        # Verify refresh was triggered for 403 as well
        assert call_count == 2
        assert final_response == mock_retry_response

    @patch('boto3.client')
    def test_aws_provider_no_refresh_on_success(self, mock_boto_client):
        """Test that successful responses don't trigger refresh."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        call_count = 0

        def mock_get_secret_value(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                'SecretString': json.dumps({
                    'token': 'success-token',
                }),
            }

        mock_client.get_secret_value.side_effect = mock_get_secret_value

        provider = AWSSecretsManagerAuthProvider()
        auth = provider.get_auth()

        # Create mock request
        mock_request = Mock(spec=requests.PreparedRequest)
        mock_request.headers = {}
        mock_request.hooks = {}

        authenticated_request = auth(mock_request)

        # Simulate successful response (200)
        mock_200_response = Mock(spec=requests.Response)
        mock_200_response.status_code = 200
        mock_200_response.request = mock_request

        # Trigger response handler
        response_handler = authenticated_request.hooks["response"][0]
        final_response = response_handler(mock_200_response)

        # Verify no refresh was triggered
        assert call_count == 1  # Only initial fetch
        assert final_response == mock_200_response  # Original response returned

    @patch('boto3.client')
    def test_aws_provider_no_double_retry(self, mock_boto_client):
        """Test that already-retried requests are not retried again."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'token': 'test-token'}),
        }

        provider = AWSSecretsManagerAuthProvider()
        auth = provider.get_auth()

        # Create mock request with retry header already set
        mock_request = Mock(spec=requests.PreparedRequest)
        mock_request.headers = {"X-MLFSA-Retried": "true"}
        mock_request.hooks = {}

        authenticated_request = auth(mock_request)

        # Simulate 401 response on already-retried request
        mock_401_response = Mock(spec=requests.Response)
        mock_401_response.status_code = 401
        mock_401_response.request = mock_request

        # Trigger response handler
        response_handler = authenticated_request.hooks["response"][0]
        final_response = response_handler(mock_401_response)

        # Verify no refresh was attempted (original response returned)
        assert final_response == mock_401_response
        # get_secret_value should only be called once (for initial auth)
        assert mock_client.get_secret_value.call_count == 1

    def teardown_method(self):
        """Clean up test environment."""
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AWS_')):
                del os.environ[key]

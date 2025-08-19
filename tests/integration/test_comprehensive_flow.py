"""Demonstration test showing both retry and auto-refresh functionality working together."""

import json
import os
from unittest.mock import Mock, patch

import requests

from mlflow_secrets_auth.providers.aws_secrets_manager import AWSSecretsManagerAuthProvider


class TestRetryAndAutoRefreshIntegration:
    """Integration test demonstrating retry + auto-refresh working together."""

    def setup_method(self):
        """Setup test environment."""
        # Clear environment
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AWS_')):
                del os.environ[key]

        # Set required environment variables
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "aws-secrets-manager"
        os.environ["AWS_REGION"] = "us-west-2"
        os.environ["MLFLOW_AWS_SECRET_ID"] = "mlflow-auth-secret"

    @patch('boto3.client')
    def test_retry_with_auto_refresh_comprehensive_flow(self, mock_boto_client):
        """Test both retry logic and auto-refresh working together."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Track total calls to get_secret_value
        call_count = 0

        def mock_get_secret_value(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # First call: transient failure, then success
            if call_count == 1:
                from botocore.exceptions import ClientError
                raise ClientError(
                    {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service temporarily unavailable'}},
                    'GetSecretValue',
                )
            if call_count == 2:
                # Retry succeeds with original token
                return {
                    'SecretString': json.dumps({
                        'token': 'original-token-123',
                    }),
                }
            # Auto-refresh fetches new token
            return {
                'SecretString': json.dumps({
                    'token': 'refreshed-token-456',
                }),
            }

        mock_client.get_secret_value.side_effect = mock_get_secret_value

        # Create provider and get auth
        provider = AWSSecretsManagerAuthProvider()
        auth = provider.get_auth()

        # Verify we have an auto-refresh auth wrapper
        from mlflow_secrets_auth.base import _AutoRefreshAuth
        assert isinstance(auth, _AutoRefreshAuth)

        # Create and authenticate a request
        mock_request = Mock(spec=requests.PreparedRequest)
        mock_request.headers = {}
        mock_request.hooks = {}
        mock_request.copy = Mock(return_value=Mock(spec=requests.PreparedRequest))
        mock_request.copy.return_value.headers = {}

        authenticated_request = auth(mock_request)

        # Verify the original token was applied (after retry)
        assert "Authorization" in authenticated_request.headers
        assert authenticated_request.headers["Authorization"] == "Bearer original-token-123"

        # Verify retry happened (call_count should be 2: fail + success)
        assert call_count == 2

        # Now simulate a 401 response to trigger auto-refresh
        mock_401_response = Mock(spec=requests.Response)
        mock_401_response.status_code = 401
        mock_401_response.request = mock_request

        # Mock successful retry response
        mock_retry_response = Mock(spec=requests.Response)
        mock_retry_response.status_code = 200

        mock_session = Mock(spec=requests.Session)
        mock_session.send.return_value = mock_retry_response
        mock_401_response.connection = mock_session

        # Trigger the response handler (auto-refresh)
        response_handler = authenticated_request.hooks["response"][0]
        final_response = response_handler(mock_401_response)

        # Verify complete flow:
        # 1. Initial auth with retry: 2 calls (fail -> success)
        # 2. Auto-refresh after 401: 1 more call
        assert call_count == 3

        # 3. Retry was sent with fresh credentials
        mock_session.send.assert_called_once()
        retry_request = mock_session.send.call_args[0][0]
        assert retry_request.headers["X-MLFSA-Retried"] == "true"
        assert retry_request.headers["Authorization"] == "Bearer refreshed-token-456"

        # 4. Final response is the successful retry
        assert final_response == mock_retry_response

    def teardown_method(self):
        """Clean up test environment."""
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AWS_')):
                del os.environ[key]

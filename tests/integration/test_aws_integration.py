"""Integration test for AWS Secrets Manager provider with mocked backend."""

import json
import os
from unittest.mock import Mock, patch

import requests

from mlflow_secrets_auth.providers.aws_secrets_manager import AWSSecretsManagerAuthProvider


class TestAWSSecretsManagerIntegration:
    """Integration tests for AWS Secrets Manager provider with mocked backend."""

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
    def test_aws_bearer_token_flow(self, mock_boto_client):
        """Test complete flow with AWS Secrets Manager and bearer token."""
        # Mock boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock secret response
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'token': 'aws-bearer-token-123',
            }),
        }

        provider = AWSSecretsManagerAuthProvider()
        auth = provider.get_auth()

        # Test the auth object
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        assert request.headers["Authorization"] == "Bearer aws-bearer-token-123"

        # Verify AWS was called correctly
        mock_boto_client.assert_called_once_with('secretsmanager', region_name='us-west-2')
        mock_client.get_secret_value.assert_called_once_with(
            SecretId="mlflow-auth-secret",
        )

    @patch('boto3.client')
    def test_aws_basic_auth_flow(self, mock_boto_client):
        """Test complete flow with AWS Secrets Manager and basic auth."""
        os.environ["MLFLOW_AWS_AUTH_MODE"] = "basic"

        # Mock boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock secret response with username/password
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'username': 'aws-user',
                'password': 'aws-pass',
            }),
        }

        provider = AWSSecretsManagerAuthProvider()
        auth = provider.get_auth()

        # Test the auth object
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        # Check basic auth header
        import base64
        expected = base64.b64encode(b"aws-user:aws-pass").decode("ascii")
        assert request.headers["Authorization"] == f"Basic {expected}"

        # Verify AWS was called correctly
        mock_boto_client.assert_called_once_with('secretsmanager', region_name='us-west-2')
        mock_client.get_secret_value.assert_called_once_with(
            SecretId="mlflow-auth-secret",
        )

    @patch('boto3.client')
    def test_aws_secret_not_found(self, mock_boto_client):
        """Test handling when secret is not found in AWS."""
        # Mock boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock secret not found
        from botocore.exceptions import ClientError
        mock_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetSecretValue',
        )

        provider = AWSSecretsManagerAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    @patch('boto3.client')
    def test_aws_caching_behavior(self, mock_client_func):
        """Test that AWS secrets are properly cached."""
        os.environ["MLFLOW_AWS_TTL_SEC"] = "2"

        # Mock boto3 client
        mock_client = Mock()
        mock_client_func.return_value = mock_client

        # Mock secret response
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'token': 'cached-token',
            }),
        }

        provider = AWSSecretsManagerAuthProvider()

        # First call should hit AWS
        provider.get_auth()
        assert mock_client.get_secret_value.call_count == 1

        # Second call should use cache
        provider.get_auth()
        assert mock_client.get_secret_value.call_count == 1

        # Manually clear cache to simulate expiry
        from mlflow_secrets_auth.cache import clear_cache
        clear_cache()

        # Third call should hit AWS again
        provider.get_auth()
        assert mock_client.get_secret_value.call_count == 2

        # Verify boto3.client was called
        mock_client_func.assert_called_with('secretsmanager', region_name='us-west-2')

    @patch('boto3.client')
    def test_aws_invalid_json_secret(self, mock_client_func):
        """Test handling of invalid JSON in secret."""
        # Mock boto3 client
        mock_client = Mock()
        mock_client_func.return_value = mock_client

        # Mock invalid JSON response that will be treated as a plain token
        mock_client.get_secret_value.return_value = {
            'SecretString': 'invalid-json-content',
        }

        provider = AWSSecretsManagerAuthProvider()

        # Should create auth object treating the content as a plain token
        auth = provider.get_auth()
        assert auth is not None

        # Test that it works as a bearer token
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        assert request.headers["Authorization"] == "Bearer invalid-json-content"

        # Verify boto3.client was called
        mock_client_func.assert_called_once_with('secretsmanager', region_name='us-west-2')

    def teardown_method(self):
        """Clean up test environment."""
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AWS_')):
                del os.environ[key]

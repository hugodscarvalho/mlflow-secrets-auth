"""Unit tests for AWS Secrets Manager provider."""

import os
from unittest.mock import patch

from mlflow_secrets_auth.providers.aws_secrets_manager import AWSSecretsManagerAuthProvider


class TestAWSSecretsManagerProvider:
    """Test AWS Secrets Manager provider."""

    def setup_method(self):
        """Setup test environment."""
        # Clear any existing environment variables
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AWS_')):
                del os.environ[key]

        # Set required environment variables
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "aws-secrets-manager"
        os.environ["AWS_REGION"] = "us-west-2"
        os.environ["MLFLOW_AWS_SECRET_ID"] = "test-secret"

    @patch('boto3.client')
    def test_provider_name(self, mock_client):
        """Test provider name."""
        provider = AWSSecretsManagerAuthProvider()
        assert provider.get_name() == "aws-secrets-manager"

    @patch('boto3.client')
    def test_provider_disabled(self, mock_client):
        """Test that disabled provider returns None."""
        del os.environ["MLFLOW_SECRETS_AUTH_ENABLE"]

        provider = AWSSecretsManagerAuthProvider()
        auth = provider.get_auth()
        assert auth is None

    @patch('boto3.client')
    def test_missing_secret_id(self, mock_client):
        """Test behavior when secret ID is not configured."""
        del os.environ["MLFLOW_AWS_SECRET_ID"]

        provider = AWSSecretsManagerAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    @patch('boto3.client')
    def test_missing_region(self, mock_client):
        """Test behavior when region is not configured."""
        del os.environ["AWS_REGION"]

        provider = AWSSecretsManagerAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    @patch('boto3.client')
    def test_custom_ttl(self, mock_client):
        """Test custom TTL configuration."""
        os.environ["MLFLOW_AWS_TTL_SEC"] = "600"

        provider = AWSSecretsManagerAuthProvider()
        assert provider._get_ttl() == 600

    @patch('boto3.client')
    def test_custom_auth_mode(self, mock_client):
        """Test custom auth mode configuration."""
        os.environ["MLFLOW_AWS_AUTH_MODE"] = "basic"

        provider = AWSSecretsManagerAuthProvider()
        assert provider._get_auth_mode() == "basic"

    def teardown_method(self):
        """Clean up test environment."""
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AWS_')):
                del os.environ[key]

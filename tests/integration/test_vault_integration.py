"""Integration test for testing with mock services."""

import os
from unittest.mock import Mock, patch

import requests

from mlflow_secrets_auth.providers.vault import VaultAuthProvider


class TestVaultIntegration:
    """Integration tests for Vault provider with mocked backend."""

    def setup_method(self):
        """Setup test environment."""
        # Clear any existing environment variables
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'VAULT_')):
                del os.environ[key]

        # Set required environment variables
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "vault"
        os.environ["VAULT_ADDR"] = "https://vault.example.com"
        os.environ["VAULT_TOKEN"] = "test-token"
        os.environ["MLFLOW_VAULT_SECRET_PATH"] = "secret/data/mlflow"

    @patch('hvac.Client')
    def test_vault_bearer_token_flow(self, mock_hvac_client):
        """Test complete flow with Vault and bearer token."""
        # Mock Vault client
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client

        # Mock successful authentication
        mock_client.is_authenticated = Mock(return_value=True)

        # Mock secret response
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            'data': {
                'data': {
                    'token': 'vault-bearer-token-123',
                },
            },
        }

        provider = VaultAuthProvider()
        auth = provider.get_request_auth("https://mlflow.example.com")

        # Test the auth object
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        assert request.headers["Authorization"] == "Bearer vault-bearer-token-123"

        # Verify Vault was called correctly
        mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
            path="mlflow",
        )

    @patch('hvac.Client')
    def test_vault_basic_auth_flow(self, mock_hvac_client):
        """Test complete flow with Vault and basic auth."""
        os.environ["MLFLOW_VAULT_AUTH_MODE"] = "basic"

        # Mock Vault client
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated = Mock(return_value=True)

        # Mock secret response with username/password
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            'data': {
                'data': {
                    'username': 'vault-user',
                    'password': 'vault-pass',
                },
            },
        }

        provider = VaultAuthProvider()
        auth = provider.get_request_auth("https://mlflow.example.com")

        # Test the auth object
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        # Check basic auth header
        import base64
        expected = base64.b64encode(b"vault-user:vault-pass").decode("ascii")
        assert request.headers["Authorization"] == f"Basic {expected}"

    @patch('hvac.Client')
    def test_vault_authentication_failure(self, mock_hvac_client):
        """Test handling of Vault authentication failure."""
        # Mock Vault client
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated = Mock(return_value=False)

        provider = VaultAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_request_auth("https://mlflow.example.com")
        assert auth is None

    @patch('hvac.Client')
    def test_vault_secret_not_found(self, mock_hvac_client):
        """Test handling when secret is not found in Vault."""
        # Mock Vault client
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated = Mock(return_value=True)

        # Mock secret not found
        from hvac.exceptions import InvalidPath
        mock_client.secrets.kv.v2.read_secret_version.side_effect = InvalidPath()

        provider = VaultAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_request_auth("https://mlflow.example.com")
        assert auth is None

    @patch('hvac.Client')
    def test_vault_caching_behavior(self, mock_hvac_client):
        """Test that Vault secrets are properly cached."""
        os.environ["MLFLOW_VAULT_TTL_SEC"] = "2"

        # Mock Vault client
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated = Mock(return_value=True)

        # Mock secret response
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            'data': {
                'data': {
                    'token': 'cached-token',
                },
            },
        }

        provider = VaultAuthProvider()

        # First call should hit Vault
        provider.get_request_auth("https://mlflow.example.com")
        assert mock_client.secrets.kv.v2.read_secret_version.call_count == 1

        # Second call should use cache
        provider.get_request_auth("https://mlflow.example.com")
        assert mock_client.secrets.kv.v2.read_secret_version.call_count == 1

        # Manually clear cache to simulate expiry
        from mlflow_secrets_auth.cache import clear_cache
        clear_cache()

        # Third call should hit Vault again after cache clear
        provider.get_request_auth("https://mlflow.example.com")
        assert mock_client.secrets.kv.v2.read_secret_version.call_count == 2

    def teardown_method(self):
        """Clean up test environment."""
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'VAULT_')):
                del os.environ[key]

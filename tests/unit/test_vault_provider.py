"""Unit tests for Vault provider."""

import os
from unittest.mock import Mock, patch

from mlflow_secrets_auth.providers.vault import VaultAuthProvider


class TestVaultProvider:
    """Test Vault provider."""

    def setup_method(self):
        """Setup test environment."""
        # Clear any existing environment variables
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'VAULT_')):
                del os.environ[key]

        # Clear cache to ensure test isolation
        from mlflow_secrets_auth.cache import clear_cache
        clear_cache()

        # Set required environment variables
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "vault"
        os.environ["VAULT_ADDR"] = "https://vault.example.com"
        os.environ["VAULT_TOKEN"] = "test-token"
        os.environ["MLFLOW_VAULT_SECRET_PATH"] = "secret/data/test"

    @patch('hvac.Client')
    def test_provider_name(self, mock_hvac_client):
        """Test provider name."""
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated.return_value = True

        provider = VaultAuthProvider()
        assert provider.get_name() == "vault"

    @patch('hvac.Client')
    def test_provider_disabled(self, mock_hvac_client):
        """Test that disabled provider returns None."""
        del os.environ["MLFLOW_SECRETS_AUTH_ENABLE"]

        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated.return_value = True

        provider = VaultAuthProvider()
        auth = provider.get_auth()
        assert auth is None

    def test_missing_vault_addr(self):
        """Test behavior when Vault address is not configured."""
        del os.environ["VAULT_ADDR"]

        provider = VaultAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    @patch('hvac.Client')
    def test_missing_secret_path(self, mock_hvac_client):
        """Test behavior when secret path is not configured."""
        del os.environ["MLFLOW_VAULT_SECRET_PATH"]

        provider = VaultAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    @patch('hvac.Client')
    def test_token_auth(self, mock_hvac_client):
        """Test token-based authentication."""
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated.return_value = True

        # Mock the secret response
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            'data': {
                'data': {
                    'token': 'test-secret-token',
                },
            },
        }

        provider = VaultAuthProvider()

        # Trigger client initialization by calling get_auth
        provider.get_auth()

        # Verify that hvac.Client was called with the correct URL
        mock_hvac_client.assert_called_once_with(url='https://vault.example.com')
        # Verify token was set
        assert mock_client.token == 'test-token'

    @patch('hvac.Client')
    def test_approle_auth(self, mock_hvac_client):
        """Test AppRole-based authentication."""
        # Remove token and set AppRole credentials
        del os.environ["VAULT_TOKEN"]
        os.environ["VAULT_ROLE_ID"] = "test-role-id"
        os.environ["VAULT_SECRET_ID"] = "test-secret-id"

        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated.return_value = True

        # Mock AppRole login response
        mock_client.auth.approle.login.return_value = {
            'auth': {'client_token': 'test-approle-token'},
        }

        # Mock the secret response
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            'data': {
                'data': {
                    'token': 'test-secret-token',
                },
            },
        }

        provider = VaultAuthProvider()
        provider._clear_client_cache()  # Clear any cached client

        # Trigger client initialization by calling get_auth
        provider.get_auth()

        # Verify AppRole auth was called
        mock_client.auth.approle.login.assert_called_once_with(
            role_id='test-role-id',
            secret_id='test-secret-id',
        )

    def test_missing_auth_credentials(self):
        """Test behavior when no auth credentials are provided."""
        del os.environ["VAULT_TOKEN"]

        provider = VaultAuthProvider()
        provider._clear_client_cache()  # Clear any cached client

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    @patch('hvac.Client')
    def test_authentication_failure(self, mock_hvac_client):
        """Test handling of authentication failure."""
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated.return_value = False

        provider = VaultAuthProvider()
        provider._clear_client_cache()  # Clear any cached client

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    @patch('hvac.Client')
    def test_custom_ttl(self, mock_hvac_client):
        """Test custom TTL configuration."""
        os.environ["MLFLOW_VAULT_TTL_SEC"] = "600"

        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated.return_value = True

        provider = VaultAuthProvider()
        assert provider._get_ttl() == 600

    @patch('hvac.Client')
    def test_custom_auth_mode(self, mock_hvac_client):
        """Test custom auth mode configuration."""
        os.environ["MLFLOW_VAULT_AUTH_MODE"] = "basic"

        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.is_authenticated.return_value = True

        provider = VaultAuthProvider()
        assert provider._get_auth_mode() == "basic"

    def teardown_method(self):
        """Clean up test environment."""
        # Clear cache to ensure test isolation
        from mlflow_secrets_auth.cache import clear_cache
        clear_cache()

        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'VAULT_')):
                del os.environ[key]

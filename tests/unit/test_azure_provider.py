"""Unit tests for Azure Key Vault provider."""

import os
from unittest.mock import patch

from mlflow_secrets_auth.providers.azure_key_vault import AzureKeyVaultAuthProvider


class TestAzureKeyVaultProvider:
    """Test Azure Key Vault provider."""

    def setup_method(self):
        """Setup test environment."""
        # Clear any existing environment variables
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AZURE_')):
                del os.environ[key]

        # Set required environment variables
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "azure-key-vault"
        os.environ["AZURE_KEY_VAULT_URL"] = "https://test.vault.azure.net/"
        os.environ["MLFLOW_AZURE_SECRET_NAME"] = "test-secret"

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_provider_name(self, mock_secret_client, mock_credential):
        """Test provider name."""
        provider = AzureKeyVaultAuthProvider()
        assert provider.get_name() == "azure-key-vault"

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_provider_disabled(self, mock_secret_client, mock_credential):
        """Test that disabled provider returns None."""
        del os.environ["MLFLOW_SECRETS_AUTH_ENABLE"]

        provider = AzureKeyVaultAuthProvider()
        auth = provider.get_auth()
        assert auth is None

    def test_missing_vault_url(self):
        """Test behavior when vault URL is not configured."""
        del os.environ["AZURE_KEY_VAULT_URL"]

        provider = AzureKeyVaultAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_missing_secret_name(self, mock_secret_client, mock_credential):
        """Test behavior when secret name is not configured."""
        del os.environ["MLFLOW_AZURE_SECRET_NAME"]

        provider = AzureKeyVaultAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_custom_ttl(self, mock_secret_client, mock_credential):
        """Test custom TTL configuration."""
        os.environ["MLFLOW_AZURE_TTL_SEC"] = "600"

        provider = AzureKeyVaultAuthProvider()
        assert provider._get_ttl() == 600

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_custom_auth_mode(self, mock_secret_client, mock_credential):
        """Test custom auth mode configuration."""
        os.environ["MLFLOW_AZURE_AUTH_MODE"] = "basic"

        provider = AzureKeyVaultAuthProvider()
        assert provider._get_auth_mode() == "basic"

    def teardown_method(self):
        """Clean up test environment."""
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AZURE_')):
                del os.environ[key]

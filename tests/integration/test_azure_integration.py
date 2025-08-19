"""Integration test for Azure Key Vault provider with mocked backend."""

import json
import os
from unittest.mock import Mock, patch

import requests

from mlflow_secrets_auth.providers.azure_key_vault import AzureKeyVaultAuthProvider


class TestAzureKeyVaultIntegration:
    """Integration tests for Azure Key Vault provider with mocked backend."""

    def setup_method(self):
        """Setup test environment."""
        # Clear any existing environment variables
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AZURE_')):
                del os.environ[key]

        # Set required environment variables
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "azure-key-vault"
        os.environ["AZURE_KEY_VAULT_URL"] = "https://test-keyvault.vault.azure.net/"
        os.environ["MLFLOW_AZURE_SECRET_NAME"] = "mlflow-auth-secret"

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_azure_bearer_token_flow(self, mock_secret_client_class, mock_credential_class):
        """Test complete flow with Azure Key Vault and bearer token."""
        # Mock Azure credential
        mock_credential = Mock()
        mock_credential_class.return_value = mock_credential

        # Mock Azure Key Vault client
        mock_client = Mock()
        mock_secret_client_class.return_value = mock_client

        # Mock secret response
        mock_secret = Mock()
        mock_secret.value = json.dumps({
            'token': 'azure-bearer-token-123',
        })
        mock_client.get_secret.return_value = mock_secret

        provider = AzureKeyVaultAuthProvider()
        auth = provider.get_auth()

        # Test the auth object
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        assert request.headers["Authorization"] == "Bearer azure-bearer-token-123"

        # Verify Azure was called correctly
        mock_secret_client_class.assert_called_once_with(
            vault_url="https://test-keyvault.vault.azure.net/",
            credential=mock_credential,
        )
        mock_client.get_secret.assert_called_once_with("mlflow-auth-secret")

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_azure_basic_auth_flow(self, mock_secret_client_class, mock_credential_class):
        """Test complete flow with Azure Key Vault and basic auth."""
        os.environ["MLFLOW_AZURE_AUTH_MODE"] = "basic"

        # Mock Azure credential
        mock_credential = Mock()
        mock_credential_class.return_value = mock_credential

        # Mock Azure Key Vault client
        mock_client = Mock()
        mock_secret_client_class.return_value = mock_client

        # Mock secret response with username/password
        mock_secret = Mock()
        mock_secret.value = json.dumps({
            'username': 'azure-user',
            'password': 'azure-pass',
        })
        mock_client.get_secret.return_value = mock_secret

        provider = AzureKeyVaultAuthProvider()
        auth = provider.get_auth()

        # Test the auth object
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        # Check basic auth header
        import base64
        expected = base64.b64encode(b"azure-user:azure-pass").decode("ascii")
        assert request.headers["Authorization"] == f"Basic {expected}"

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_azure_secret_not_found(self, mock_secret_client_class, mock_credential_class):
        """Test handling when secret is not found in Azure."""
        # Mock Azure credential
        mock_credential = Mock()
        mock_credential_class.return_value = mock_credential

        # Mock Azure Key Vault client
        mock_client = Mock()
        mock_secret_client_class.return_value = mock_client

        # Mock secret not found
        from azure.core.exceptions import ResourceNotFoundError
        mock_client.get_secret.side_effect = ResourceNotFoundError("Secret not found")

        provider = AzureKeyVaultAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_azure_caching_behavior(self, mock_secret_client_class, mock_credential_class):
        """Test that Azure secrets are properly cached."""
        os.environ["MLFLOW_AZURE_TTL_SEC"] = "2"

        # Mock Azure credential
        mock_credential = Mock()
        mock_credential_class.return_value = mock_credential

        # Mock Azure Key Vault client
        mock_client = Mock()
        mock_secret_client_class.return_value = mock_client

        # Mock secret response
        mock_secret = Mock()
        mock_secret.value = json.dumps({
            'token': 'cached-token',
        })
        mock_client.get_secret.return_value = mock_secret

        provider = AzureKeyVaultAuthProvider()

        # First call should hit Azure
        provider.get_auth()
        assert mock_client.get_secret.call_count == 1

        # Second call should use cache
        provider.get_auth()
        assert mock_client.get_secret.call_count == 1

        # Manually clear cache to simulate expiry
        from mlflow_secrets_auth.cache import clear_cache
        clear_cache()

        # Third call should hit Azure again after cache clear
        provider.get_auth()
        assert mock_client.get_secret.call_count == 2

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_azure_invalid_json_secret(self, mock_secret_client_class, mock_credential_class):
        """Test handling of invalid JSON in secret."""
        # Mock Azure credential
        mock_credential = Mock()
        mock_credential_class.return_value = mock_credential

        # Mock Azure Key Vault client
        mock_client = Mock()
        mock_secret_client_class.return_value = mock_client

        # Mock invalid JSON response that will be treated as a plain token
        mock_secret = Mock()
        mock_secret.value = 'invalid-json-content'
        mock_client.get_secret.return_value = mock_secret

        provider = AzureKeyVaultAuthProvider()

        # Should create auth object treating the content as a plain token
        auth = provider.get_auth()
        assert auth is not None

        # Test that it works as a bearer token
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        assert request.headers["Authorization"] == "Bearer invalid-json-content"

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.keyvault.secrets.SecretClient')
    def test_azure_authentication_failure(self, mock_secret_client_class, mock_credential_class):
        """Test handling of Azure authentication failure."""
        # Mock Azure credential failure
        from azure.core.exceptions import ClientAuthenticationError
        mock_credential_class.side_effect = ClientAuthenticationError("Authentication failed")

        provider = AzureKeyVaultAuthProvider()

        # Should return None instead of raising exception
        auth = provider.get_auth()
        assert auth is None

    def teardown_method(self):
        """Clean up test environment."""
        for key in os.environ.copy():
            if key.startswith(('MLFLOW_', 'AZURE_')):
                del os.environ[key]

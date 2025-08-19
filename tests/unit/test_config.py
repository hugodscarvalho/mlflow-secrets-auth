"""Unit tests for configuration utilities."""

import os

from mlflow_secrets_auth.config import (
    get_env_var,
    get_auth_header_name,
    get_allowed_hosts,
    is_provider_enabled,
)


class TestConfig:
    """Test configuration utilities."""

    def setup_method(self):
        """Setup test environment."""
        # Clear any existing environment variables
        for key in os.environ.copy():
            if key.startswith('MLFLOW_'):
                del os.environ[key]

    def test_get_env_var_with_provider_prefix(self):
        """Test getting environment variable with provider prefix."""
        os.environ["MLFLOW_VAULT_SECRET_PATH"] = "/secret/path"

        result = get_env_var("MLFLOW_VAULT_SECRET_PATH")
        assert result == "/secret/path"

    def test_get_env_var_without_provider_prefix(self):
        """Test getting environment variable without provider prefix."""
        os.environ["MLFLOW_AUTH_HEADER_NAME"] = "X-Custom-Auth"

        result = get_env_var("MLFLOW_AUTH_HEADER_NAME")
        assert result == "X-Custom-Auth"

    def test_get_env_var_with_default(self):
        """Test getting environment variable with default value."""
        result = get_env_var("NONEXISTENT_VAR", "default_value")
        assert result == "default_value"

    def test_get_env_var_missing_returns_none(self):
        """Test that missing variable returns None."""
        result = get_env_var("NONEXISTENT_VAR")
        assert result is None

    def test_get_auth_header_name_default(self):
        """Test default auth header name."""
        result = get_auth_header_name()
        assert result == "Authorization"

    def test_get_auth_header_name_custom(self):
        """Test custom auth header name."""
        os.environ["MLFLOW_AUTH_HEADER_NAME"] = "X-API-Key"
        result = get_auth_header_name()
        assert result == "X-API-Key"

    def test_get_allowed_hosts_none(self):
        """Test when no allowed hosts are configured."""
        result = get_allowed_hosts()
        assert result is None

    def test_get_allowed_hosts_single(self):
        """Test single allowed host."""
        os.environ["MLFLOW_SECRETS_ALLOWED_HOSTS"] = "mlflow.example.com"
        result = get_allowed_hosts()
        assert result == ["mlflow.example.com"]

    def test_get_allowed_hosts_multiple(self):
        """Test multiple allowed hosts."""
        os.environ["MLFLOW_SECRETS_ALLOWED_HOSTS"] = "host1.com,host2.com,host3.com"
        result = get_allowed_hosts()
        assert result == ["host1.com", "host2.com", "host3.com"]

    def test_get_allowed_hosts_with_spaces(self):
        """Test allowed hosts with spaces."""
        os.environ["MLFLOW_SECRETS_ALLOWED_HOSTS"] = " host1.com , host2.com , host3.com "
        result = get_allowed_hosts()
        assert result == ["host1.com", "host2.com", "host3.com"]

    def test_is_provider_enabled_true(self):
        """Test when provider is enabled."""
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "vault"
        assert is_provider_enabled("vault") is True
        assert is_provider_enabled("aws-secrets-manager") is False

    def test_is_provider_enabled_false(self):
        """Test when no provider is enabled."""
        assert is_provider_enabled("vault") is False
        assert is_provider_enabled("aws-secrets-manager") is False

    def teardown_method(self):
        """Clean up test environment."""
        for key in os.environ.copy():
            if key.startswith('MLFLOW_'):
                del os.environ[key]

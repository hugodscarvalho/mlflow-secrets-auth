"""Unit tests for the base auth provider."""

import base64
import os
import time
from unittest.mock import Mock

import requests

from mlflow_secrets_auth.base import SecretsBackedAuthProvider


class MockAuthProvider(SecretsBackedAuthProvider):
    """Test implementation of the base provider."""

    def __init__(self):
        self._test_secret = {"token": "test-token-123"}
        super().__init__("test", 300)

    def _fetch_secret(self) -> dict:
        import json
        return json.dumps(self._test_secret)

    def _get_auth_mode(self) -> str:
        return os.environ.get("MLFLOW_TEST_AUTH_MODE", "bearer")

    def _get_ttl(self) -> int:
        return int(os.environ.get("MLFLOW_TEST_TTL_SEC", "300"))

    def _get_cache_key(self) -> str:
        return "test_provider_cache"

    def set_test_secret(self, secret: dict):
        """Helper method to set test secret."""
        self._test_secret = secret


class TestSecretsBackedAuthProvider:
    """Test the base auth provider functionality."""

    def setup_method(self):
        """Setup test environment."""
        # Clear any existing environment variables
        for key in os.environ.copy():
            if key.startswith('MLFLOW_'):
                del os.environ[key]

        self.provider = MockAuthProvider()

    def test_bearer_token_auth(self):
        """Test bearer token authentication."""
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "test"
        self.provider.set_test_secret({"token": "test-bearer-token"})

        auth = self.provider.get_auth()

        # Test the auth object
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        assert request.headers["Authorization"] == "Bearer test-bearer-token"

    def test_basic_auth(self):
        """Test basic authentication."""
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "test"
        os.environ["MLFLOW_TEST_AUTH_MODE"] = "basic"
        self.provider = MockAuthProvider()
        self.provider.set_test_secret({
            "username": "testuser",
            "password": "testpass",
        })

        auth = self.provider.get_auth()

        # Test the auth object
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        # Should set Authorization header
        assert "Authorization" in request.headers
        expected = base64.b64encode(b"testuser:testpass").decode('utf-8')
        assert request.headers["Authorization"] == f"Basic {expected}"

    def test_custom_header_name(self):
        """Test custom authentication header name."""
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "test"
        os.environ["MLFLOW_AUTH_HEADER_NAME"] = "X-Custom-Auth"
        self.provider = MockAuthProvider()
        self.provider.set_test_secret({"token": "custom-token"})

        auth = self.provider.get_auth()

        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}
        auth(request)

        assert request.headers["X-Custom-Auth"] == "custom-token"
        assert "Authorization" not in request.headers

    def test_host_allowlist(self):
        """Test host allowlist functionality."""
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "test"
        os.environ["MLFLOW_SECRETS_ALLOWED_HOSTS"] = "mlflow.example.com,trusted.example.com"
        self.provider = MockAuthProvider()

        # Allowed host should get auth
        auth = self.provider.get_request_auth("https://mlflow.example.com/api/2.0/")
        assert auth is not None

        # Disallowed host should not get auth
        auth = self.provider.get_request_auth("https://untrusted.example.com/api/2.0/")
        assert auth is None

    def test_caching(self):
        """Test secret caching functionality."""
        # Use short TTL for testing
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "test"
        os.environ["MLFLOW_TEST_TTL_SEC"] = "1"

        self.provider = MockAuthProvider()
        call_count = 0
        original_fetch = self.provider._fetch_secret

        def counting_fetch():
            nonlocal call_count
            call_count += 1
            return original_fetch()

        self.provider._fetch_secret = counting_fetch

        # First call should fetch from backend
        self.provider.get_auth()
        assert call_count == 1

        # Second call should use cache
        self.provider.get_auth()
        assert call_count == 1

        # Wait for cache to expire
        time.sleep(1.1)

        # Third call should fetch from backend again
        self.provider.get_auth()
        assert call_count == 2

    def test_invalid_secret_format(self):
        """Test handling of invalid secret format."""
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "test"
        self.provider = MockAuthProvider()
        self.provider.set_test_secret({"invalid": "format"})

        # Should return None instead of raising exception
        auth = self.provider.get_auth()
        assert auth is None

    def test_backend_error_handling(self):
        """Test error handling when backend fails."""
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "test"
        self.provider = MockAuthProvider()

        def failing_fetch():
            msg = "Backend error"
            raise Exception(msg)

        self.provider._fetch_secret = failing_fetch

        # Should return None instead of raising exception
        auth = self.provider.get_auth()
        assert auth is None

    def test_disabled_provider(self):
        """Test that disabled provider returns None."""
        # Don't set the enable flag
        auth = self.provider.get_auth()
        assert auth is None

    def teardown_method(self):
        """Clean up test environment."""
        for key in os.environ.copy():
            if key.startswith('MLFLOW_'):
                del os.environ[key]

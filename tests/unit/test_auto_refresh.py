"""Unit tests for auto-refresh authentication functionality."""

import json
import os
from unittest.mock import Mock

import requests

from mlflow_secrets_auth.base import (
    _AutoRefreshAuth,
    SecretsBackedAuthProvider,
    BearerAuth,
    BasicAuth,
)
from mlflow_secrets_auth.cache import delete_cache_key, clear_cache


class TestAutoRefreshAuth:
    """Test _AutoRefreshAuth functionality."""

    def setup_method(self):
        """Setup test environment."""
        # Clear cache before each test
        clear_cache()

        # Clear environment variables
        for key in os.environ.copy():
            if key.startswith('MLFLOW_'):
                del os.environ[key]

    def test_successful_request_no_refresh(self):
        """Test that successful requests pass through without refresh."""
        # Create mock auth and provider
        mock_auth = Mock(spec=BearerAuth)
        mock_provider = Mock(spec=SecretsBackedAuthProvider)

        auto_auth = _AutoRefreshAuth(mock_auth, mock_provider, "test:cache:key")

        # Create a mock request with proper hooks dict
        request = Mock(spec=requests.PreparedRequest)
        request.headers = {}
        request.hooks = {}  # Start with empty dict

        # Mock the auth to return the request (common pattern)
        mock_auth.return_value = request

        # Apply authentication
        result_request = auto_auth(request)

        # Verify auth was applied
        mock_auth.assert_called_once_with(request)

        # Verify response hook was added
        assert "response" in result_request.hooks
        assert len(result_request.hooks["response"]) == 1

        # Test successful response (no refresh should happen)
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.request = request

        response_handler = result_request.hooks["response"][0]
        final_response = response_handler(response)

        # Should return original response without calling provider
        assert final_response == response
        mock_provider.get_auth.assert_not_called()

    def test_401_response_triggers_refresh_and_retry(self):
        """Test that 401 response triggers cache bust and retry."""
        # Create mock auth and provider
        mock_auth = Mock(spec=BearerAuth)
        mock_provider = Mock(spec=SecretsBackedAuthProvider)
        mock_provider.logger = Mock()
        mock_provider._fetch_secret_cached = Mock(return_value={"token": "new-token"})
        mock_provider._create_auth = Mock()

        # Create fresh auth for retry
        fresh_auth = Mock(spec=BearerAuth)
        mock_provider._create_auth.return_value = fresh_auth

        auto_auth = _AutoRefreshAuth(mock_auth, mock_provider, "test:cache:key")

        # Create mock 401 response
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 401
        mock_response.request = Mock(spec=requests.PreparedRequest)
        mock_response.request.headers = {}
        mock_response.request.copy = Mock(return_value=Mock(spec=requests.PreparedRequest))
        mock_response.request.copy.return_value.headers = {}

        # Create mock session for retry
        mock_session = Mock(spec=requests.Session)
        mock_retry_response = Mock(spec=requests.Response)
        mock_retry_response.status_code = 200
        mock_session.send.return_value = mock_retry_response

        # Mock the session access
        mock_response.connection = mock_session

        # Call the response handler
        result = auto_auth._handle_auth_failure(mock_response)

        # Verify cache was busted (would need to mock delete_cache_key to test this)
        # Verify fresh credentials were fetched
        mock_provider._fetch_secret_cached.assert_called_once()

        # Verify fresh auth was created
        mock_provider._create_auth.assert_called_once_with({"token": "new-token"})

        # Verify request was retried
        mock_session.send.assert_called_once()

        # Verify retry response was returned
        assert result == mock_retry_response

    def test_403_response_triggers_refresh_and_retry(self):
        """Test that 403 response also triggers cache bust and retry."""
        mock_auth = Mock(spec=BearerAuth)
        mock_provider = Mock(spec=SecretsBackedAuthProvider)
        mock_provider.logger = Mock()
        mock_provider._fetch_secret_cached = Mock(return_value={"token": "new-token"})
        mock_provider._create_auth = Mock()

        fresh_auth = Mock(spec=BearerAuth)
        mock_provider._create_auth.return_value = fresh_auth

        auto_auth = _AutoRefreshAuth(mock_auth, mock_provider, "test:cache:key")

        # Create mock 403 response
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 403
        mock_response.request = Mock(spec=requests.PreparedRequest)
        mock_response.request.headers = {}
        mock_response.request.copy = Mock(return_value=Mock(spec=requests.PreparedRequest))
        mock_response.request.copy.return_value.headers = {}

        mock_session = Mock(spec=requests.Session)
        mock_retry_response = Mock(spec=requests.Response)
        mock_retry_response.status_code = 200
        mock_session.send.return_value = mock_retry_response
        mock_response.connection = mock_session

        result = auto_auth._handle_auth_failure(mock_response)

        # Verify refresh was attempted
        mock_provider._fetch_secret_cached.assert_called_once()
        mock_provider._create_auth.assert_called_once()
        mock_session.send.assert_called_once()
        assert result == mock_retry_response

    def test_already_retried_request_not_retried_again(self):
        """Test that requests already marked as retried are not retried again."""
        mock_auth = Mock(spec=BearerAuth)
        mock_provider = Mock(spec=SecretsBackedAuthProvider)
        mock_provider.logger = Mock()

        auto_auth = _AutoRefreshAuth(mock_auth, mock_provider, "test:cache:key")

        # Create mock 401 response with retry header
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 401
        mock_response.request = Mock(spec=requests.PreparedRequest)
        mock_response.request.headers = {"X-MLFSA-Retried": "true"}

        result = auto_auth._handle_auth_failure(mock_response)

        # Should return original response without retry
        assert result == mock_response

        # Verify no refresh was attempted
        mock_provider._fetch_secret_cached.assert_not_called()

    def test_non_auth_error_status_codes_ignored(self):
        """Test that non-401/403 status codes are ignored."""
        mock_auth = Mock(spec=BearerAuth)
        mock_provider = Mock(spec=SecretsBackedAuthProvider)

        auto_auth = _AutoRefreshAuth(mock_auth, mock_provider, "test:cache:key")

        # Test various non-auth error status codes
        for status_code in [200, 404, 500, 502]:
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = status_code
            mock_response.request = Mock(spec=requests.PreparedRequest)
            mock_response.request.headers = {}

            result = auto_auth._handle_auth_failure(mock_response)

            # Should return original response
            assert result == mock_response

            # Verify no refresh was attempted
            mock_provider._fetch_secret_cached.assert_not_called()

    def test_refresh_credentials_failure_returns_original_response(self):
        """Test that failure to refresh credentials returns original response."""
        mock_auth = Mock(spec=BearerAuth)
        mock_provider = Mock(spec=SecretsBackedAuthProvider)
        mock_provider.logger = Mock()
        mock_provider._fetch_secret_cached = Mock(return_value=None)  # Simulate failure

        auto_auth = _AutoRefreshAuth(mock_auth, mock_provider, "test:cache:key")

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 401
        mock_response.request = Mock(spec=requests.PreparedRequest)
        mock_response.request.headers = {}

        result = auto_auth._handle_auth_failure(mock_response)

        # Should return original response when refresh fails
        assert result == mock_response

        # Verify warning was logged
        mock_provider.logger.log.assert_called()

    def test_exception_during_refresh_returns_original_response(self):
        """Test that exceptions during refresh are handled gracefully."""
        mock_auth = Mock(spec=BearerAuth)
        mock_provider = Mock(spec=SecretsBackedAuthProvider)
        mock_provider.logger = Mock()
        mock_provider._fetch_secret_cached = Mock(side_effect=Exception("Refresh failed"))

        auto_auth = _AutoRefreshAuth(mock_auth, mock_provider, "test:cache:key")

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 401
        mock_response.request = Mock(spec=requests.PreparedRequest)
        mock_response.request.headers = {}

        result = auto_auth._handle_auth_failure(mock_response)

        # Should return original response when exception occurs
        assert result == mock_response

        # Verify error was logged
        mock_provider.logger.log.assert_called()

    def test_retry_request_marked_with_header(self):
        """Test that retry requests are marked with X-MLFSA-Retried header."""
        mock_auth = Mock(spec=BearerAuth)
        mock_provider = Mock(spec=SecretsBackedAuthProvider)
        mock_provider.logger = Mock()
        mock_provider._fetch_secret_cached = Mock(return_value={"token": "new-token"})

        fresh_auth = Mock(spec=BearerAuth)
        mock_provider._create_auth = Mock(return_value=fresh_auth)

        auto_auth = _AutoRefreshAuth(mock_auth, mock_provider, "test:cache:key")

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 401

        # Create mock request with copy method
        original_request = Mock(spec=requests.PreparedRequest)
        original_request.headers = {}
        retry_request = Mock(spec=requests.PreparedRequest)
        retry_request.headers = {}
        original_request.copy = Mock(return_value=retry_request)
        mock_response.request = original_request

        mock_session = Mock(spec=requests.Session)
        mock_retry_response = Mock(spec=requests.Response)
        mock_retry_response.status_code = 200
        mock_session.send.return_value = mock_retry_response
        mock_response.connection = mock_session

        auto_auth._handle_auth_failure(mock_response)

        # Verify retry header was added
        assert retry_request.headers["X-MLFSA-Retried"] == "true"

        # Verify fresh auth was applied to retry request
        fresh_auth.assert_called_once_with(retry_request)


class TestSecretsBackedAuthProviderAutoRefresh:
    """Test auto-refresh integration in SecretsBackedAuthProvider."""

    def setup_method(self):
        """Setup test environment."""
        clear_cache()
        for key in os.environ.copy():
            if key.startswith('MLFLOW_'):
                del os.environ[key]

    def test_create_auth_wraps_with_auto_refresh(self):
        """Test that _create_auth wraps auth objects with auto-refresh."""
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "test"

        # Create a test provider
        class TestProvider(SecretsBackedAuthProvider):
            def _fetch_secret(self):
                return json.dumps({"token": "test-token"})

            def _get_cache_key(self):
                return "test-key"

            def _get_auth_mode(self):
                return "bearer"

            def _get_ttl(self):
                return 300

        provider = TestProvider("test", 300)
        secret_data = {"token": "test-token"}

        auth = provider._create_auth(secret_data)

        # Verify it's wrapped with _AutoRefreshAuth
        assert isinstance(auth, _AutoRefreshAuth)
        assert isinstance(auth.auth, BearerAuth)
        assert auth.provider == provider
        assert auth.cache_key == "test:test-key"

    def test_integration_with_get_auth(self):
        """Test integration of auto-refresh with get_auth method."""
        os.environ["MLFLOW_SECRETS_AUTH_ENABLE"] = "test"

        class TestProvider(SecretsBackedAuthProvider):
            def _fetch_secret(self):
                return json.dumps({"username": "user", "password": "pass"})

            def _get_cache_key(self):
                return "test-key"

            def _get_auth_mode(self):
                return "basic"

            def _get_ttl(self):
                return 300

        provider = TestProvider("test", 300)
        auth = provider.get_auth()

        # Verify it's wrapped with auto-refresh
        assert isinstance(auth, _AutoRefreshAuth)
        assert isinstance(auth.auth, BasicAuth)

    def teardown_method(self):
        """Clean up test environment."""
        clear_cache()
        for key in os.environ.copy():
            if key.startswith('MLFLOW_'):
                del os.environ[key]


class TestCacheKeyDeletion:
    """Test cache key deletion functionality."""

    def setup_method(self):
        """Setup test environment."""
        clear_cache()

    def test_delete_existing_cache_key(self):
        """Test deleting an existing cache key."""
        from mlflow_secrets_auth.cache import _global_cache

        # Add a key to cache
        _global_cache.set("test:key", "test-value", 300)
        assert _global_cache.get("test:key") == "test-value"

        # Delete the key
        delete_cache_key("test:key")
        assert _global_cache.get("test:key") is None

    def test_delete_nonexistent_cache_key(self):
        """Test deleting a non-existent cache key doesn't raise error."""
        # Should not raise any exception
        delete_cache_key("nonexistent:key")

    def teardown_method(self):
        """Clean up test environment."""
        clear_cache()

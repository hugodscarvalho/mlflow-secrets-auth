"""Unit tests for caching functionality."""

import time
from unittest.mock import patch

from mlflow_secrets_auth.cache import TTLCache


class TestTTLCache:
    """Test TTL cache functionality."""

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = TTLCache()

        cache.set("key1", "value1", 60)
        assert cache.get("key1") == "value1"

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_cache_expiry(self):
        """Test that cached items expire after TTL."""
        cache = TTLCache()

        cache.set("key1", "value1", 1)
        assert cache.get("key1") == "value1"

        # Wait for expiry
        time.sleep(1.1)

        assert cache.get("key1") is None

    def test_cache_update_existing_key(self):
        """Test updating existing key in cache."""
        cache = TTLCache()

        cache.set("key1", "value1", 60)
        cache.set("key1", "value2", 60)

        assert cache.get("key1") == "value2"

    def test_cache_clear(self):
        """Test cache clear functionality."""
        cache = TTLCache()

        cache.set("key1", "value1", 60)
        cache.set("key2", "value2", 60)

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_size(self):
        """Test cache size reporting."""
        cache = TTLCache()

        assert cache.size() == 0

        cache.set("key1", "value1", 60)
        assert cache.size() == 1

        cache.set("key2", "value2", 60)
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0

    @patch('mlflow_secrets_auth.cache.time.monotonic')
    def test_cache_expiry_with_mock_time(self, mock_time):
        """Test cache expiry using mocked monotonic time."""
        # Start at time 0
        mock_time.return_value = 0

        cache = TTLCache()
        cache.set("key1", "value1", 300)

        # Move forward 200 seconds (within TTL)
        mock_time.return_value = 200
        assert cache.get("key1") == "value1"

        # Move forward 400 seconds (beyond TTL)
        mock_time.return_value = 400
        assert cache.get("key1") is None

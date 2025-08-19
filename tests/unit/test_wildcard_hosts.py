"""Tests for wildcard host allowlist functionality."""


from mlflow_secrets_auth.utils import is_host_allowed


class TestWildcardHostAllowlist:
    """Test wildcard patterns in host allowlisting."""

    def test_none_allowlist_allows_all(self):
        """Test that None allowlist allows all hosts."""
        assert is_host_allowed("https://any.example.com/path", None) is True
        assert is_host_allowed("http://malicious.com", None) is True
        assert is_host_allowed("https://localhost:8080", None) is True

    def test_exact_hostname_matching(self):
        """Test exact hostname matching (no wildcards)."""
        allowed = ["example.com", "api.prod.com", "localhost"]

        # Exact matches should work
        assert is_host_allowed("https://example.com/api", allowed) is True
        assert is_host_allowed("http://api.prod.com:8080/health", allowed) is True
        assert is_host_allowed("https://localhost/admin", allowed) is True

        # Non-matches should be rejected
        assert is_host_allowed("https://sub.example.com", allowed) is False
        assert is_host_allowed("https://api.staging.com", allowed) is False
        assert is_host_allowed("https://evil.com", allowed) is False

    def test_wildcard_subdomain_patterns(self):
        """Test wildcard patterns for subdomains."""
        allowed = ["*.example.com", "api.*.com"]

        # Subdomain wildcards should match
        assert is_host_allowed("https://api.example.com", allowed) is True
        assert is_host_allowed("https://web.example.com/path", allowed) is True
        assert is_host_allowed("https://very.long.subdomain.example.com", allowed) is True

        # Middle wildcards should match
        assert is_host_allowed("https://api.prod.com", allowed) is True
        assert is_host_allowed("https://api.staging.com", allowed) is True

        # Non-matches should be rejected
        assert is_host_allowed("https://example.com", allowed) is False  # No subdomain
        assert is_host_allowed("https://example.org", allowed) is False  # Wrong TLD
        assert is_host_allowed("https://web.api.staging.com", allowed) is False  # Extra subdomain

    def test_wildcard_prefix_patterns(self):
        """Test wildcard patterns for prefixes."""
        allowed = ["api-*", "mlflow-*.corp.com"]

        # Prefix wildcards should match
        assert is_host_allowed("https://api-prod", allowed) is True
        assert is_host_allowed("https://api-staging.local", allowed) is True
        assert is_host_allowed("https://mlflow-prod.corp.com", allowed) is True
        assert is_host_allowed("https://mlflow-staging.corp.com", allowed) is True

        # Non-matches should be rejected
        assert is_host_allowed("https://web-prod", allowed) is False
        assert is_host_allowed("https://api", allowed) is False  # No suffix
        assert is_host_allowed("https://mlflow.corp.com", allowed) is False  # Missing hyphen

    def test_complex_wildcard_patterns(self):
        """Test more complex wildcard patterns."""
        allowed = ["*.*.example.com", "mlflow-*-prod.com"]

        # Multi-level wildcards
        assert is_host_allowed("https://api.v1.example.com", allowed) is True
        assert is_host_allowed("https://web.staging.example.com", allowed) is True

        # Complex middle patterns
        assert is_host_allowed("https://mlflow-eu-prod.com", allowed) is True
        assert is_host_allowed("https://mlflow-us-west-prod.com", allowed) is True

        # Non-matches
        assert is_host_allowed("https://api.example.com", allowed) is False  # Not enough levels
        assert is_host_allowed("https://mlflow-staging.com", allowed) is False  # Wrong suffix

    def test_mixed_exact_and_wildcard_patterns(self):
        """Test mixing exact matches with wildcard patterns."""
        allowed = ["localhost", "*.staging.com", "api.prod.example.com", "mlflow-*"]

        # Exact matches
        assert is_host_allowed("https://localhost:8080", allowed) is True
        assert is_host_allowed("https://api.prod.example.com", allowed) is True

        # Wildcard matches
        assert is_host_allowed("https://web.staging.com", allowed) is True
        assert is_host_allowed("https://mlflow-dev", allowed) is True
        assert is_host_allowed("https://mlflow-production.local", allowed) is True

        # Non-matches
        assert is_host_allowed("https://api.staging.example.com", allowed) is False
        assert is_host_allowed("https://web.prod.com", allowed) is False

    def test_case_sensitivity(self):
        """Test that hostname matching is case-insensitive (as per DNS standards)."""
        allowed = ["*.Example.COM", "API.prod.com"]

        # Different cases should all match
        assert is_host_allowed("https://api.example.com", allowed) is True
        assert is_host_allowed("https://API.EXAMPLE.COM", allowed) is True
        assert is_host_allowed("https://Web.Example.Com", allowed) is True
        assert is_host_allowed("https://api.prod.com", allowed) is True
        assert is_host_allowed("https://API.PROD.COM", allowed) is True

    def test_empty_hostname_handling(self):
        """Test handling of URLs with missing or invalid hostnames."""
        allowed = ["*.example.com"]

        # Invalid URLs should be rejected
        assert is_host_allowed("not-a-url", allowed) is False
        assert is_host_allowed("", allowed) is False
        assert is_host_allowed("file:///local/path", allowed) is False

    def test_port_handling(self):
        """Test that ports are ignored in hostname matching."""
        allowed = ["*.example.com", "localhost"]

        # Ports should be stripped from hostname comparison
        assert is_host_allowed("https://api.example.com:8080", allowed) is True
        assert is_host_allowed("https://web.example.com:443", allowed) is True
        assert is_host_allowed("https://localhost:3000", allowed) is True
        assert is_host_allowed("https://localhost:8000/path", allowed) is True

    def test_single_character_wildcards(self):
        """Test single character wildcards using '?'."""
        allowed = ["api?.example.com", "host?"]

        # Single character wildcards
        assert is_host_allowed("https://api1.example.com", allowed) is True
        assert is_host_allowed("https://apia.example.com", allowed) is True
        assert is_host_allowed("https://host1", allowed) is True
        assert is_host_allowed("https://hosta", allowed) is True

        # Should not match multiple characters
        assert is_host_allowed("https://api12.example.com", allowed) is False
        assert is_host_allowed("https://host12", allowed) is False

    def test_bracket_patterns(self):
        """Test character class patterns using brackets."""
        allowed = ["api[0-9].example.com", "host[abc]"]

        # Character ranges and classes
        assert is_host_allowed("https://api1.example.com", allowed) is True
        assert is_host_allowed("https://api9.example.com", allowed) is True
        assert is_host_allowed("https://hosta", allowed) is True
        assert is_host_allowed("https://hostb", allowed) is True
        assert is_host_allowed("https://hostc", allowed) is True

        # Should not match outside the class
        assert is_host_allowed("https://apia.example.com", allowed) is False
        assert is_host_allowed("https://hostd", allowed) is False
        assert is_host_allowed("https://host1", allowed) is False

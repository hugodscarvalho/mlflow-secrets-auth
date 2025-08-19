"""Unit tests for utility functions."""


import pytest

from mlflow_secrets_auth.utils import (
    retry_with_jitter,
    parse_secret_json,
    format_duration,
    validate_ttl,
    mask_secret,
)


class TestRetryWithJitter:
    """Test retry_with_jitter functionality."""

    def test_retry_success_on_first_attempt(self):
        """Test successful function call on first attempt."""
        def success_fn():
            return "success"

        result = retry_with_jitter(success_fn)
        assert result == "success"

    def test_retry_success_after_failures(self):
        """Test successful function call after retries."""
        call_count = 0

        def retry_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = f"Failure {call_count}"
                raise Exception(msg)
            return f"success on attempt {call_count}"

        result = retry_with_jitter(retry_then_success, attempts=3)
        assert result == "success on attempt 3"
        assert call_count == 3

    def test_retry_all_attempts_fail(self):
        """Test that all attempts fail and last exception is raised."""
        def always_fail():
            msg = "Always fails"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="Always fails"):
            retry_with_jitter(always_fail, attempts=2)

    def test_retry_with_custom_parameters(self):
        """Test retry with custom parameters."""
        call_count = 0
        sleep_calls = []

        def mock_sleep(duration):
            sleep_calls.append(duration)

        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = f"Fail {call_count}"
                raise Exception(msg)
            return "success"

        result = retry_with_jitter(
            fail_twice,
            attempts=3,
            base_delay=0.1,
            backoff=2.0,
            max_delay=1.0,
            jitter=0.4,
            sleep=mock_sleep,
        )

        assert result == "success"
        assert call_count == 3
        assert len(sleep_calls) == 2  # Should sleep between attempts 1-2 and 2-3

        # Verify that sleep delays are in reasonable ranges (with jitter)
        # Base delay = 0.1, so with jitter, should be roughly 0.1 ± 0.04 (40%)
        assert 0.06 <= sleep_calls[0] <= 0.14, f"First delay {sleep_calls[0]} out of expected range"

        # Second delay = 0.2 (0.1 * 2^1), with jitter should be roughly 0.2 ± 0.08
        assert 0.12 <= sleep_calls[1] <= 0.28, f"Second delay {sleep_calls[1]} out of expected range"

    def test_retry_no_sleep_after_last_attempt(self):
        """Test that no sleep occurs after the final failed attempt."""
        sleep_calls = []

        def mock_sleep(duration):
            sleep_calls.append(duration)

        def always_fail():
            msg = "Always fails"
            raise Exception(msg)

        with pytest.raises(Exception, match="Always fails"):
            retry_with_jitter(always_fail, attempts=2, sleep=mock_sleep)

        # Should only sleep once (between attempts 1 and 2)
        assert len(sleep_calls) == 1

    def test_retry_max_delay_cap(self):
        """Test that delays are capped by max_delay."""
        sleep_calls = []

        def mock_sleep(duration):
            sleep_calls.append(duration)

        def fail_many_times():
            msg = "Always fails"
            raise Exception(msg)

        with pytest.raises(Exception):
            retry_with_jitter(
                fail_many_times,
                attempts=5,
                base_delay=1.0,
                backoff=10.0,  # Large backoff
                max_delay=2.0,  # Small max delay
                jitter=0.0,  # No jitter for predictable testing
                sleep=mock_sleep,
            )

        # All delays should be capped at max_delay (2.0)
        for delay in sleep_calls:
            assert delay <= 2.0

    def test_retry_zero_jitter(self):
        """Test retry with zero jitter for predictable delays."""
        sleep_calls = []

        def mock_sleep(duration):
            sleep_calls.append(duration)

        def fail_three_times():
            if len(sleep_calls) < 2:  # Will fail first 2 attempts
                msg = "Fail"
                raise Exception(msg)
            return "success"

        result = retry_with_jitter(
            fail_three_times,
            attempts=3,
            base_delay=0.1,
            backoff=2.0,
            max_delay=10.0,
            jitter=0.0,  # No jitter
            sleep=mock_sleep,
        )

        assert result == "success"
        # With no jitter, delays should be exactly base_delay * backoff^attempt
        assert sleep_calls[0] == 0.1  # 0.1 * 2^0
        assert sleep_calls[1] == 0.2  # 0.1 * 2^1

    def test_retry_with_different_exception_types(self):
        """Test that different exception types are properly propagated."""
        def fail_with_value_error():
            msg = "Value error"
            raise ValueError(msg)

        def fail_with_runtime_error():
            msg = "Runtime error"
            raise RuntimeError(msg)

        with pytest.raises(ValueError, match="Value error"):
            retry_with_jitter(fail_with_value_error, attempts=2)

        with pytest.raises(RuntimeError, match="Runtime error"):
            retry_with_jitter(fail_with_runtime_error, attempts=2)


class TestParseSecretJson:
    """Test parse_secret_json functionality."""

    def test_parse_json_token(self):
        """Test parsing JSON with token field."""
        secret = '{"token": "test-token-123"}'
        result = parse_secret_json(secret)
        assert result == {"token": "test-token-123"}

    def test_parse_json_username_password(self):
        """Test parsing JSON with username/password fields."""
        secret = '{"username": "user123", "password": "pass456"}'
        result = parse_secret_json(secret)
        assert result == {"username": "user123", "password": "pass456"}

    def test_parse_plain_token(self):
        """Test parsing plain string token."""
        result = parse_secret_json("plain-token-value")
        assert result == {"token": "plain-token-value"}

    def test_parse_plain_username_password(self):
        """Test parsing plain string username:password."""
        result = parse_secret_json("user:pass")
        assert result == {"username": "user", "password": "pass"}

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON falls back to plain string."""
        result = parse_secret_json("not-json-token")
        assert result == {"token": "not-json-token"}

    def test_parse_empty_secret(self):
        """Test parsing empty secret raises ValueError."""
        with pytest.raises(ValueError, match="Secret is empty"):
            parse_secret_json("")

        with pytest.raises(ValueError, match="Secret is empty"):
            parse_secret_json("   ")

    def test_parse_invalid_json_object(self):
        """Test parsing JSON object with invalid fields."""
        with pytest.raises(ValueError, match="Secret must contain either"):
            parse_secret_json('{"invalid": "field"}')

    def test_parse_json_with_whitespace(self):
        """Test that whitespace is stripped from JSON fields."""
        secret = '{"token": "  token-with-spaces  "}'
        result = parse_secret_json(secret)
        assert result == {"token": "token-with-spaces"}


class TestFormatDuration:
    """Test format_duration functionality."""

    def test_format_seconds(self):
        """Test formatting seconds."""
        assert format_duration(45) == "45s"
        assert format_duration(1) == "1s"

    def test_format_minutes(self):
        """Test formatting minutes."""
        assert format_duration(60) == "1m"
        assert format_duration(125) == "2m 5s"
        assert format_duration(120) == "2m"

    def test_format_hours(self):
        """Test formatting hours."""
        assert format_duration(3600) == "1h"
        assert format_duration(3660) == "1h 1m"
        assert format_duration(7200) == "2h"


class TestValidateTtl:
    """Test validate_ttl functionality."""

    def test_validate_valid_ttl(self):
        """Test validating valid TTL values."""
        assert validate_ttl(300) == 300
        assert validate_ttl(600) == 600

    def test_validate_none_ttl(self):
        """Test validating None TTL uses default."""
        assert validate_ttl(None) == 300  # Default

    def test_validate_zero_ttl(self):
        """Test validating zero TTL uses default."""
        assert validate_ttl(0) == 300  # Default

    def test_validate_negative_ttl(self):
        """Test validating negative TTL uses default."""
        assert validate_ttl(-10) == 300  # Default

    def test_validate_ttl_with_custom_default(self):
        """Test validating TTL with custom default."""
        assert validate_ttl(None, default=600) == 600
        assert validate_ttl(0, default=600) == 600

    def test_validate_ttl_clamping(self):
        """Test TTL clamping to min/max values."""
        # Float gets converted to int(0) -> default 300 is used
        assert validate_ttl(0.5, min_ttl=1, default=300) == 300
        assert validate_ttl(5000, max_ttl=3600) == 3600  # Clamped to max
        # Test actual clamping with valid integers
        assert validate_ttl(0, min_ttl=5, default=300) == 300  # 0 -> default -> clamped to min
        assert validate_ttl(1, min_ttl=5) == 5  # Below min, clamped up


class TestMaskSecret:
    """Test mask_secret functionality."""

    def test_mask_long_secret(self):
        """Test masking long secret."""
        result = mask_secret("abcdefghijklmnop", show_chars=4)
        assert result == "abcd...mnop"

    def test_mask_short_secret(self):
        """Test masking short secret."""
        result = mask_secret("abc")
        assert result == "***"

    def test_mask_empty_secret(self):
        """Test masking empty secret."""
        result = mask_secret("")
        assert result == "***"

    def test_mask_with_custom_show_chars(self):
        """Test masking with custom show_chars."""
        result = mask_secret("abcdefghijklmnop", show_chars=2)
        assert result == "ab...op"

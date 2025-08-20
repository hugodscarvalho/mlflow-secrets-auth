"""Utility functions for MLflow secrets auth providers.

This module centralizes:
  * Logger setup with environment-driven log levels.
  * Safe logging with automatic redaction of sensitive substrings.
  * Secret parsing with automatic format detection (JSON vs. plain string).
  * URL allowlist checks.
  * Small helpers (duration formatting, TTL validation, masking).
  * Retry functionality with exponential backoff and jitter.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import random
import time
from typing import Any, TypeVar
from collections.abc import Callable
from urllib.parse import urlparse
from .constants import (
    DEFAULT_MASK_CHAR,
    DEFAULT_SHOW_CHARS,
    DEFAULT_TTL_SECONDS,
    MAX_TTL_SECONDS,
    MIN_TTL_SECONDS,
    SECRET_FIELD_PASSWORD,
    SECRET_FIELD_TOKEN,
    SECRET_FIELD_USERNAME,
)
from .messages import (
    ERROR_SECRET_EMPTY,
    ERROR_SECRET_INVALID_JSON,
    ERROR_SECRET_TOKEN_INVALID,
    ERROR_SECRET_USERNAME_INVALID,
    ERROR_SECRET_PASSWORD_INVALID,
    ERROR_SECRET_MISSING_FIELDS,
)
from .config import get_log_level, redact_sensitive_data


def setup_logger(name: str) -> logging.Logger:
    """Create or configure a namespaced logger.

    The logger level is always driven by the `MLFLOW_SECRETS_LOG_LEVEL` env var.
    A single stream handler is attached once; propagation is disabled to avoid
    duplicated messages under test runners or frameworks.

    Args:
        name: Logger name (typically package.module).

    Returns:
        A configured `logging.Logger` instance.

    """
    logger = logging.getLogger(name)

    # Always set the level from config
    level_name = get_log_level()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    # Only add a handler if none exist (avoid duplicate logs under pytest)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Avoid double logging through parent loggers
    logger.propagate = False
    return logger


def safe_log(logger: logging.Logger, level: int, message: str, *args: Any) -> None:
    """Log a message with automatic redaction of sensitive data.

    The message is first formatted with `args` (printf-style) and only then
    passed through the redactor to avoid leaking secrets via formatting.

    Args:
        logger: Target logger.
        level: Logging level (e.g., `logging.INFO`).
        message: Format string.
        *args: Arguments for printf-style substitution.

    """
    if args:
        try:
            message = message % args
        except Exception:
            # Fall back to a simple join if interpolation fails for any reason
            message = " ".join([message, *map(str, args)])
    redacted_message = redact_sensitive_data(message)
    logger.log(level, redacted_message)


def parse_secret_json(secret_value: str) -> dict[str, str]:
    """Parse secret material with automatic format detection.

    Accepts either:
      * JSON object with one of:
          - {"token": "<opaque token>"}
          - {"username": "...", "password": "..."}
      * Plain string:
          - "username:password" → {"username": "...", "password": "..."}
          - "<token>" → {"token": "<token>"}

    Whitespace is stripped from string fields.

    Args:
        secret_value: Raw secret value.

    Returns:
        A normalized dict with either {"token": "..."} or {"username": "...", "password": "..."}.

    Raises:
        ValueError: If the JSON object is invalid or missing required fields.

    """
    # First attempt: JSON object
    try:
        data = json.loads(secret_value)
    except json.JSONDecodeError:
        # Fallback to plain string
        value = secret_value.strip()
        if not value:
            raise ValueError(ERROR_SECRET_EMPTY) from None

        if ":" in value:
            username, password = value.split(":", 1)
            username = (username or "").strip()
            password = (password or "").strip()
            if not username or not username.strip():
                raise ValueError(ERROR_SECRET_USERNAME_INVALID) from None
            if not password or not password.strip():
                raise ValueError(ERROR_SECRET_PASSWORD_INVALID) from None
            return {SECRET_FIELD_USERNAME: username, SECRET_FIELD_PASSWORD: password}
        return {SECRET_FIELD_TOKEN: value}

    if not isinstance(data, dict):
        raise ValueError(ERROR_SECRET_INVALID_JSON)

    # Token-based secret
    if SECRET_FIELD_TOKEN in data:
        token = data[SECRET_FIELD_TOKEN]
        if not isinstance(token, str) or not token.strip():
            raise ValueError(ERROR_SECRET_TOKEN_INVALID)
        return {SECRET_FIELD_TOKEN: token.strip()}

    # Username/password secret
    if SECRET_FIELD_USERNAME in data and SECRET_FIELD_PASSWORD in data:
        username = data[SECRET_FIELD_USERNAME]
        password = data[SECRET_FIELD_PASSWORD]
        if not isinstance(username, str) or not username.strip():
            raise ValueError(ERROR_SECRET_USERNAME_INVALID)
        if not isinstance(password, str) or not password.strip():
            raise ValueError(ERROR_SECRET_PASSWORD_INVALID)
        return {SECRET_FIELD_USERNAME: username.strip(), SECRET_FIELD_PASSWORD: password.strip()}

    raise ValueError(
        ERROR_SECRET_MISSING_FIELDS,
    )


def is_host_allowed(url: str, allowed_hosts: list[str] | None) -> bool:
    """Return whether the URL's host is in the provided allowlist.

    Supports exact hostname matches and wildcard patterns using shell-style
    globbing (e.g., "*.corp.example.com" matches "api.corp.example.com").

    Hostname matching is case-insensitive as per DNS standards.

    Examples:
        - "example.com" matches exactly "example.com"
        - "*.corp.example.com" matches "api.corp.example.com", "web.corp.example.com"
        - "mlflow.*.com" matches "mlflow.prod.com", "mlflow.staging.com"

    Args:
        url: Full URL to check.
        allowed_hosts: List of allowed hostname patterns, or None to allow all.

    Returns:
        True if allowed (or no allowlist configured), otherwise False.

    """
    if allowed_hosts is None:
        return True
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return False

        # Normalize hostname to lowercase for case-insensitive comparison
        hostname = hostname.lower()

        # Check each pattern in the allowlist
        for pattern in allowed_hosts:
            # Normalize pattern to lowercase as well
            pattern_lower = pattern.lower()
            if fnmatch.fnmatch(hostname, pattern_lower):
                return True

        return False
    except Exception:
        return False


def format_duration(seconds: int) -> str:
    """Format a duration in seconds into a short human-readable string.

    Examples:
        45 -> "45s"
        125 -> "2m 5s"
        3600 -> "1h"

    Args:
        seconds: Duration in seconds.

    Returns:
        Short human-readable representation.

    """
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m" if s == 0 else f"{m}m {s}s"
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    return f"{h}h" if m == 0 else f"{h}h {m}m"


def validate_ttl(
    ttl_seconds: int | None,
    *,
    default: int = DEFAULT_TTL_SECONDS,
    min_ttl: int = MIN_TTL_SECONDS,
    max_ttl: int = MAX_TTL_SECONDS,
) -> int:
    """Validate and clamp a TTL value.

    Rules:
      * If `ttl_seconds` is None or <= 0, use `default`.
      * Clamp the final value between `min_ttl` and `max_ttl` (inclusive).

    Args:
        ttl_seconds: Requested TTL in seconds.
        default: Fallback TTL when input is invalid or not provided.
        min_ttl: Minimum allowed TTL (inclusive).
        max_ttl: Maximum allowed TTL (inclusive).

    Returns:
        A valid TTL in seconds.

    """
    try:
        ttl = int(ttl_seconds) if ttl_seconds is not None else int(default)
    except (TypeError, ValueError):
        ttl = int(default)

    if ttl <= 0:
        ttl = int(default)

    if ttl < min_ttl:
        ttl = min_ttl
    elif ttl > max_ttl:
        ttl = max_ttl

    return ttl


def mask_secret(secret: str, show_chars: int = DEFAULT_SHOW_CHARS) -> str:
    """Mask a secret for safe logging.

    For short inputs (<= 2 * show_chars) returns a generic "***" to avoid
    revealing almost the entire secret.

    Args:
        secret: Secret value.
        show_chars: Number of leading and trailing characters to keep.

    Returns:
        Masked representation of the secret.

    """
    if not secret or len(secret) <= show_chars * 2:
        return DEFAULT_MASK_CHAR * 3
    return f"{secret[:show_chars]}...{secret[-show_chars:]}"


T = TypeVar("T")


def retry_with_jitter(
    fn: Callable[[], T],
    attempts: int = 3,
    base_delay: float = 0.1,
    backoff: float = 2.0,
    max_delay: float = 1.0,
    jitter: float = 0.4,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Retry a function with exponential backoff and jitter.

    Calls `fn` up to `attempts` times with exponential backoff and ±jitter%,
    capped by `max_delay`. If all attempts fail, reraises the last exception.

    Args:
        fn: Function to call (should take no arguments).
        attempts: Maximum number of attempts (must be >= 1).
        base_delay: Initial delay in seconds.
        backoff: Exponential backoff multiplier.
        max_delay: Maximum delay between attempts in seconds.
        jitter: Jitter factor as a proportion (e.g., 0.4 = ±40%).
        sleep: Sleep function (mainly for testing).

    Returns:
        Result of the successful function call.

    Raises:
        Exception: The last exception encountered if all attempts fail.

    """
    last_exception = None

    for attempt in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exception = e

            # Don't sleep after the last attempt
            if attempt == attempts - 1:
                break

            # Calculate delay with exponential backoff
            delay = min(base_delay * (backoff ** attempt), max_delay)

            # Add jitter: ±jitter% of the delay
            jitter_amount = delay * jitter * (2 * random.random() - 1)  # noqa: S311
            final_delay = max(0, delay + jitter_amount)

            sleep(final_delay)

    # Re-raise the last exception if all attempts failed
    if last_exception is not None:
        raise last_exception

    # This should never happen, but just in case
    msg = "No attempts were made"
    raise RuntimeError(msg)


__all__ = [
    "format_duration",
    "is_host_allowed",
    "mask_secret",
    "parse_secret_json",
    "retry_with_jitter",
    "safe_log",
    "setup_logger",
    "validate_ttl",
]

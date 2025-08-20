"""Configuration utilities for MLflow secrets auth providers.

This module centralizes environment-driven configuration and safe redaction helpers.

Key env vars:
  * MLFLOW_SECRETS_ALLOWED_HOSTS: Comma-separated host allowlist.
  * MLFLOW_AUTH_HEADER_NAME: Custom header for auth (defaults to "Authorization").
  * MLFLOW_SECRETS_LOG_LEVEL: Logging level (defaults to "INFO").
  * MLFLOW_SECRETS_AUTH_ENABLE: Comma-separated list of enabled providers.
  * MLFLOW_SECRETS_AUTH_ENABLE_<PROVIDER>: Per-provider boolean toggle (e.g., AWS_SECRETS_MANAGER).
"""

from __future__ import annotations

import os
import re
from typing import Final

from .constants import (
    DEFAULT_AUTH_HEADER,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MASK_CHAR,
    DEFAULT_SHOW_CHARS,
    ENV_ALLOWED_HOSTS,
    ENV_AUTH_HEADER_NAME,
    ENV_LOG_LEVEL,
    ENV_AUTH_ENABLE,
    TRUTHY_VALUES,
    ENV_AUTH_ENABLE_PREFIX,
)


def get_env_var(name: str, default: str | None = None) -> str | None:
    """Return an environment variable or a default.

    Args:
        name: Environment variable name.
        default: Value to return if not set.

    Returns:
        The environment value as a string, or `default` when unset.

    """
    return os.environ.get(name, default)


def get_env_bool(name: str, default: bool = False) -> bool:
    """Return an environment variable parsed as a boolean.

    Recognized truthy values (case-insensitive): {"1", "true", "yes", "on"}.

    Args:
        name: Environment variable name.
        default: Fallback when the variable is unset.

    Returns:
        Parsed boolean value.

    """
    value = get_env_var(name)
    if value is None:
        return default
    return value.strip().lower() in TRUTHY_VALUES


def get_env_int(name: str, default: int) -> int:
    """Return an environment variable parsed as int.

    On parsing error or if unset, returns `default`.

    Args:
        name: Environment variable name.
        default: Fallback value.

    Returns:
        Parsed integer or `default`.

    """
    value = get_env_var(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def get_allowed_hosts() -> list[str] | None:
    """Return the host allowlist from MLFLOW_SECRETS_ALLOWED_HOSTS.

    Supports both exact hostnames and wildcard patterns using shell-style globbing.

    Examples:
        MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.example.com,*.corp.example.com"
        MLFLOW_SECRETS_ALLOWED_HOSTS="api.prod.com,*.staging.com,localhost"

    Wildcard patterns:
        - "*.corp.example.com" matches any subdomain of corp.example.com
        - "mlflow.*.com" matches mlflow with any middle component
        - "api-*" matches hostnames starting with "api-"

    Returns:
        A list of hostname patterns, or None if not configured.

    """
    hosts_str = get_env_var(ENV_ALLOWED_HOSTS)
    if not hosts_str:
        return None
    hosts = [h.strip() for h in hosts_str.split(",") if h.strip()]
    return hosts or None


def get_auth_header_name() -> str:
    """Return the configured auth header name.

    Defaults to "Authorization" when MLFLOW_AUTH_HEADER_NAME is unset.

    Returns:
        Header name as a string.

    """
    return get_env_var(ENV_AUTH_HEADER_NAME, DEFAULT_AUTH_HEADER) or DEFAULT_AUTH_HEADER


def get_log_level() -> str:
    """Return the configured log level for secrets auth.

    Defaults to "INFO" and uppercases the value for consistency.

    Returns:
        Uppercased logging level string (e.g., "INFO", "DEBUG").

    """
    return (get_env_var(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL) or DEFAULT_LOG_LEVEL).upper()


def is_provider_enabled(provider_name: str) -> bool:
    """Return whether a specific provider is enabled.

    Two mechanisms:
      1) Global list: MLFLOW_SECRETS_AUTH_ENABLE="vault,aws-secrets-manager,azure-key-vault"
      2) Per-provider boolean: MLFLOW_SECRETS_AUTH_ENABLE_<PROVIDER>=true
         e.g. MLFLOW_SECRETS_AUTH_ENABLE_AWS_SECRETS_MANAGER=true

    Args:
        provider_name: Provider slug (case-insensitive), e.g. "vault".

    Returns:
        True if enabled via either mechanism, False otherwise.

    """
    # Global list
    global_enable = get_env_var(ENV_AUTH_ENABLE, "") or ""
    enabled = {p.strip().lower() for p in global_enable.split(",") if p.strip()}
    if provider_name.strip().lower() in enabled:
        return True

    # Provider-specific toggle
    env_key = f"{ENV_AUTH_ENABLE_PREFIX}{provider_name.upper().replace('-', '_')}"
    return get_env_bool(env_key, False)


def mask_secret(value: str, mask_char: str = DEFAULT_MASK_CHAR, show_chars: int = DEFAULT_SHOW_CHARS) -> str:
    """Mask a secret value for safe logging.

    Examples:
        >>> mask_secret("abcd1234")
        'abcd********1234'
        >>> mask_secret("ab")
        '***'

    Args:
        value: Secret value to mask.
        mask_char: Masking character (default '*').
        show_chars: Number of leading and trailing chars to keep (default 4).

    Returns:
        Masked representation with the center portion obfuscated.

    """
    if not value:
        return mask_char * 8

    # Guard against non-positive show_chars
    show = max(0, int(show_chars))

    if len(value) <= show:
        return mask_char * max(3, len(value))
    if len(value) <= show * 2:
        # Keep a small preview while masking the middle
        keep = min(2, len(value))
        return f"{value[:keep]}{mask_char * 4}{value[-keep:]}"
    return f"{value[:show]}{mask_char * 8}{value[-show:]}"


# Pre-compiled patterns for `redact_sensitive_data`
_REDACT_PATTERNS: Final[list[re.Pattern[str]]] = [
    # Bearer tokens: "Bearer <token>"
    re.compile(r"(Bearer\s+)([A-Za-z0-9._\-]+)"),
    # Basic auth: "Basic <b64>"
    re.compile(r"(Basic\s+)([A-Za-z0-9+/=]+)"),
    # JWT-like tokens (three dot-separated base64url segments)
    re.compile(r"(eyJ[A-Za-z0-9._\-]+\.[A-Za-z0-9._\-]+\.[A-Za-z0-9._\-]+)"),
    # JSON fields: "token" / "password" / "secret" / "key"
    re.compile(r'("(?:token|password|secret|key)"\s*:\s*")([^"]+)(")'),
    # URL with credentials: https://user:pass@host
    re.compile(r"(https?://[^:]+:)([^@]+)(@)"),
]


def redact_sensitive_data(text: str) -> str:
    """Redact common credential patterns from text.

    Safely handles patterns with different group counts. Intended for logs and messages.

    Args:
        text: Input string possibly containing sensitive material.

    Returns:
        Redacted string with secrets masked.

    """
    if not text:
        return text

    def _sub(m: re.Match[str]) -> str:
        groups = m.groups()
        # One-group pattern: mask entire match
        if len(groups) == 1:
            return mask_secret(groups[0])
        # Two/three-group patterns: mask the middle secret
        if len(groups) >= 2:
            prefix = groups[0]
            secret = groups[1]
            suffix = groups[2] if len(groups) >= 3 else ""
            return f"{prefix}{mask_secret(secret)}{suffix}"
        # Fallback to original text (should not happen with defined patterns)
        return m.group(0)

    result = text
    for pattern in _REDACT_PATTERNS:
        result = pattern.sub(_sub, result)
    return result


__all__ = [
    "get_allowed_hosts",
    "get_auth_header_name",
    "get_env_bool",
    "get_env_int",
    "get_env_var",
    "get_log_level",
    "is_provider_enabled",
    "mask_secret",
    "redact_sensitive_data",
]

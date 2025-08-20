"""Base classes and abstractions for MLflow secrets-backed authentication providers.

This module defines:
  * Lightweight `requests.auth.AuthBase` implementations for Bearer, Basic, and custom-header auth.
  * `SecretsBackedAuthProvider`, an abstract base for MLflow `RequestAuthProvider`s that obtain
    credentials from secret managers and cache them with a TTL.

Design notes:
  * Providers implement `_fetch_secret`, `_get_cache_key`, `_get_auth_mode`, and `_get_ttl`.
  * Caching is delegated to `cached_fetch` and TTL validation to `validate_ttl`.
  * Secrets are parsed centrally via `parse_secret_json` and must resolve to either:
      - {"token": "<opaque or bearer token>"}  OR
      - {"username": "...", "password": "..."}
  * Header name can be configured; "Authorization" is normalized to the canonical header.

All logging goes through `safe_log` to avoid leaking sensitive values.
"""

from __future__ import annotations

import base64
import logging
from abc import ABC, abstractmethod
from typing import Literal, TypedDict
from urllib.parse import urlparse

import requests
from mlflow.tracking.request_auth.abstract_request_auth_provider import (
    RequestAuthProvider,
)

from .cache import cached_fetch, delete_cache_key
from .config import get_allowed_hosts, get_auth_header_name, is_provider_enabled
from .utils import (
    is_host_allowed,
    parse_secret_json,
    safe_log,
    setup_logger,
    validate_ttl,
)

from .constants import (
    AUTH_MODE_BEARER,
    AUTH_MODE_BASIC,
    DEFAULT_AUTH_HEADER,
    DEFAULT_TTL_SECONDS,
    HEADER_RETRY_MARKER,
    HEADER_RETRY_VALUE,
    SECRET_FIELD_PASSWORD,
    SECRET_FIELD_TOKEN,
    SECRET_FIELD_USERNAME,
)

from .messages import (
    ERROR_REFRESH_FAILED,
    INFO_RETRYING_REQUEST,
    INFO_RETRY_COMPLETED,
    ERROR_REFRESH_AND_RETRY,
    DEBUG_PROVIDER_NOT_ENABLED,
    ERROR_UNEXPECTED_PROVIDER,
    INFO_HOST_NOT_ALLOWED,
    WARNING_FETCH_FAILED,
    WARNING_CONFIG_ERROR,
    ERROR_BASIC_TOKEN_FORMAT,
    ERROR_BEARER_WITH_USERPASS,
    ERROR_SECRET_MISSING_TOKEN_OR_CREDS,
    WARNING_INVALID_TTL,
)


AuthMode = Literal["bearer", "basic"]


class SecretData(TypedDict, total=False):
    """Structured representation of parsed secret material."""

    token: str
    username: str
    password: str


def _normalize_header_name(header_name: str | None) -> str:
    """Normalize the configured auth header name.

    Ensures that any case-insensitive variant of "Authorization" becomes the canonical
    HTTP header "Authorization". Falls back to "Authorization" if `header_name` is falsy.

    Args:
        header_name: Configured header name (may be None or any case).

    Returns:
        A canonical HTTP header name.

    """
    if not header_name:
        return DEFAULT_AUTH_HEADER
    return DEFAULT_AUTH_HEADER if header_name.lower() == DEFAULT_AUTH_HEADER.lower() else header_name


class BearerAuth(requests.auth.AuthBase):
    """Bearer token authentication for `requests`.

    The token is injected as: `<header_name>: Bearer <token>`

    Attributes:
        token: Opaque bearer token.
        header_name: Target header (defaults to "Authorization").

    """

    __slots__ = ("header_name", "token")

    def __init__(self, token: str, header_name: str = DEFAULT_AUTH_HEADER) -> None:
        """Initialize bearer authentication.

        Args:
            token: Bearer token string.
            header_name: HTTP header to inject (defaults to "Authorization").

        """
        self.token = token
        self.header_name = header_name

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """Attach the bearer token header to the outgoing request."""
        r.headers[self.header_name] = f"Bearer {self.token}"
        return r


class BasicAuth(requests.auth.AuthBase):
    """HTTP Basic authentication for `requests`.

    If a non-standard header is configured, the base64 credentials are put into that header.

    Attributes:
        username: Basic auth username.
        password: Basic auth password.
        header_name: Target header (defaults to "Authorization").

    """

    __slots__ = ("header_name", "password", "username")

    def __init__(self, username: str, password: str, header_name: str = DEFAULT_AUTH_HEADER) -> None:
        """Initialize basic authentication.

        Args:
            username: Username for basic auth.
            password: Password for basic auth.
            header_name: HTTP header to inject (defaults to "Authorization").

        """
        self.username = username
        self.password = password
        self.header_name = header_name

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """Attach the basic auth header to the outgoing request."""
        creds = f"{self.username}:{self.password}".encode()
        r.headers[self.header_name] = f"Basic {base64.b64encode(creds).decode()}"
        return r


class CustomHeaderAuth(requests.auth.AuthBase):
    """Custom header authentication for `requests` (token placed as-is).

    Attributes:
        token: Opaque token to inject.
        header_name: Target header.

    """

    __slots__ = ("header_name", "token")

    def __init__(self, token: str, header_name: str) -> None:
        """Initialize custom header authentication.

        Args:
            token: Token value to inject directly.
            header_name: Header name where the token is placed.

        """
        self.token = token
        self.header_name = header_name

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """Attach the opaque token to the configured header."""
        r.headers[self.header_name] = self.token
        return r


class _AutoRefreshAuth(requests.auth.AuthBase):
    """Auto-refreshing authentication wrapper.

    Wraps another AuthBase and automatically handles 401/403 responses by:
    1. Busting the provider's cache key
    2. Refetching fresh credentials
    3. Retrying the request once

    Attributes:
        auth: The wrapped authentication object.
        provider: The secrets provider instance.
        cache_key: Cache key to invalidate on auth failure.

    """

    __slots__ = ("auth", "cache_key", "provider")

    def __init__(
        self,
        auth: requests.auth.AuthBase,
        provider: SecretsBackedAuthProvider,
        cache_key: str,
    ) -> None:
        self.auth = auth
        self.provider = provider
        self.cache_key = cache_key

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """Apply authentication and set up response hook for auto-refresh."""
        # Apply the underlying authentication
        r = self.auth(r)

        # Add response hook for handling auth failures
        r.hooks = getattr(r, "hooks", {})
        if "response" not in r.hooks:
            r.hooks["response"] = []
        elif not isinstance(r.hooks["response"], list):
            r.hooks["response"] = [r.hooks["response"]]

        r.hooks["response"].append(self._handle_auth_failure)
        return r

    def _handle_auth_failure(self, response: requests.Response, *_args, **_kwargs) -> requests.Response:
        """Handle authentication failures by refreshing credentials and retrying once."""
        # Only handle 401/403 responses and avoid retry loops
        if (
            response.status_code not in (401, 403) or
            response.request.headers.get(HEADER_RETRY_MARKER) == HEADER_RETRY_VALUE
        ):
            return response

        try:
            # Bust the cache and refetch credentials
            delete_cache_key(self.cache_key)
            secret_data = self.provider._fetch_secret_cached()  # noqa: SLF001
            if not secret_data:
                safe_log(
                    self.provider.logger,
                    logging.WARNING,
                    ERROR_REFRESH_FAILED.format(status_code=response.status_code),
                )
                return response

            # Create fresh auth object
            fresh_auth = self.provider._create_auth(secret_data)  # noqa: SLF001

            # Clone the original request
            retry_request = response.request.copy()
            retry_request.headers[HEADER_RETRY_MARKER] = HEADER_RETRY_VALUE

            # Apply fresh authentication
            retry_request = fresh_auth(retry_request)

            # Retry the request
            safe_log(
                self.provider.logger,
                logging.DEBUG,
                INFO_RETRYING_REQUEST.format(status_code=response.status_code),
            )

            # Use the same session to maintain connection pooling
            session = getattr(response, "connection", None) or requests.Session()
            retry_response = session.send(retry_request)

            safe_log(
                self.provider.logger,
                logging.DEBUG,
                INFO_RETRY_COMPLETED.format(status_code=retry_response.status_code),
            )

            return retry_response

        except Exception as e:
            safe_log(
                self.provider.logger,
                logging.ERROR,
                ERROR_REFRESH_AND_RETRY.format(error=e),
            )
            return response


class SecretsBackedAuthProvider(RequestAuthProvider, ABC):
    """Abstract base class for secrets-backed MLflow auth providers.

    Subclasses implement secret retrieval for a specific backend (e.g., Vault, AWS, Azure)
    and supply configuration inputs (cache key, auth mode, TTL).

    This class handles:
      * Provider enablement checks.
      * Host allowlisting for `get_request_auth`.
      * Cache + TTL validation.
      * Secret parsing and Auth object construction.

    Args:
        provider_name: Stable identifier used for logging and configuration.
        default_ttl: Fallback TTL in seconds if configured TTL is invalid.

    Attributes:
        provider_name: Provider identifier.
        default_ttl: Default TTL for cache.
        logger: Namespaced logger instance.

    """

    def __init__(self, provider_name: str, default_ttl: int = DEFAULT_TTL_SECONDS) -> None:
        """Initialize the provider base.

        Args:
            provider_name: Identifier of the provider (e.g., "vault").
            default_ttl: Default cache TTL in seconds.

        """
        self.provider_name = provider_name
        self.default_ttl = default_ttl
        self.logger = setup_logger(f"mlflow_secrets_auth.{provider_name}")

    # MLflow-required interface

    def get_name(self) -> str:
        """Return the provider name (instance method in recent MLflow versions).

        Returns:
            Provider name for MLflow plugin discovery.

        """
        return self.provider_name

    def get_auth(self) -> requests.auth.AuthBase | None:
        """Return a `requests` Auth object (no URL filtering).

        This method is used by MLflow when a per-request URL is not available.

        Returns:
            A `requests.auth.AuthBase` instance or None when disabled/unavailable.

        """
        if not self._is_enabled():
            safe_log(self.logger, logging.DEBUG, DEBUG_PROVIDER_NOT_ENABLED.format(provider=self.provider_name))
            return None

        try:
            secret_data = self._fetch_secret_cached()
            return None if not secret_data else self._create_auth(secret_data)
        except Exception as e:  # pragma: no cover — defensive guard
            safe_log(self.logger, logging.ERROR, ERROR_UNEXPECTED_PROVIDER.format(provider=self.provider_name, error=e))
            return None

    def get_request_auth(self, url: str) -> requests.auth.AuthBase | None:
        """Return a `requests` Auth object for a given MLflow request URL.

        Applies host allowlisting to avoid credential leakage.

        Args:
            url: Full request URL for an MLflow call.

        Returns:
            A `requests.auth.AuthBase` instance or None if not allowed/available.

        """
        if not self._is_enabled():
            safe_log(self.logger, logging.DEBUG, DEBUG_PROVIDER_NOT_ENABLED.format(provider=self.provider_name))
            return None

        allowed_hosts = get_allowed_hosts()
        if not is_host_allowed(url, allowed_hosts):
            hostname = urlparse(url).hostname or "<unknown>"
            safe_log(
                self.logger,
                logging.INFO,
                INFO_HOST_NOT_ALLOWED.format(hostname=hostname),
            )
            return None

        try:
            secret_data = self._fetch_secret_cached()
            if not secret_data:
                safe_log(self.logger, logging.WARNING, WARNING_FETCH_FAILED.format(provider=self.provider_name))
                return None
            return self._create_auth(secret_data)
        except ValueError as e:
            # Configuration or parsing error — not fatal to the request.
            safe_log(self.logger, logging.WARNING, WARNING_CONFIG_ERROR.format(provider=self.provider_name, error=e))
            return None
        except Exception as e:  # pragma: no cover — defensive
            safe_log(self.logger, logging.ERROR, ERROR_UNEXPECTED_PROVIDER.format(provider=self.provider_name, error=e))
            return None

    # Core helpers

    def _is_enabled(self) -> bool:
        """Check whether this provider is enabled via configuration.

        Returns:
            True if the provider is enabled, False otherwise.

        """
        return is_provider_enabled(self.provider_name)

    def _validated_ttl(self) -> int:
        """Validate TTL while remaining compatible with different `validate_ttl` signatures.

        Returns:
            A positive TTL in seconds. Falls back to `default_ttl` when invalid.

        """
        raw = self._get_ttl()
        try:
            # Newer style: (ttl, fallback) as positionals
            return validate_ttl(raw, self.default_ttl)  # type: ignore[misc]
        except TypeError:
            # Older style: validate_ttl(ttl) only
            try:
                return validate_ttl(raw)  # type: ignore[misc]
            except Exception:
                safe_log(
                    self.logger,
                    logging.WARNING,
                    WARNING_INVALID_TTL.format(raw=raw, default=self.default_ttl),
                )
                return self.default_ttl

    def _fetch_secret_cached(self) -> SecretData | None:
        """Fetch and parse the secret with caching and TTL validation.

        Returns:
            Parsed `SecretData` dict or None when not available.

        """
        cache_key = f"{self.provider_name}:{self._get_cache_key()}"
        ttl = self._validated_ttl()

        @cached_fetch(cache_key, ttl)
        def _fetch() -> SecretData | None:
            raw = self._fetch_secret()
            if raw is None:
                return None
            return parse_secret_json(raw)

        return _fetch()

    def _create_auth(self, secret: SecretData) -> requests.auth.AuthBase:
        """Create a `requests` Auth object from parsed secret material.

        Supports:
          * Bearer mode with token in "Authorization" (or custom header via `CustomHeaderAuth`).
          * Basic mode using either "username/password" fields or a "token" formatted as
            "username:password".

        Args:
            secret: Parsed secret data.

        Returns:
            A concrete `requests.auth.AuthBase` instance wrapped with auto-refresh capability.

        Raises:
            ValueError: On invalid combinations (e.g., bearer mode with username/password).

        """
        auth_mode: AuthMode = self._get_auth_mode()
        header_name = _normalize_header_name(get_auth_header_name())

        # Create the underlying auth object
        auth: requests.auth.AuthBase

        # Token provisioned
        if SECRET_FIELD_TOKEN in secret:
            token = secret[SECRET_FIELD_TOKEN]
            if auth_mode == AUTH_MODE_BASIC:
                # Accept token in the form "username:password" for convenience.
                if ":" not in token:
                    msg = ERROR_BASIC_TOKEN_FORMAT
                    raise ValueError(msg)
                username, password = token.split(":", 1)
                auth = BasicAuth(username, password, header_name)
            elif header_name == DEFAULT_AUTH_HEADER:
                # Bearer or opaque token in custom header
                auth = BearerAuth(token, header_name)
            else:
                auth = CustomHeaderAuth(token, header_name)

        # Username/password provisioned
        elif SECRET_FIELD_USERNAME in secret and SECRET_FIELD_PASSWORD in secret:
            if auth_mode == AUTH_MODE_BEARER:
                msg = ERROR_BEARER_WITH_USERPASS
                raise ValueError(msg)
            auth = BasicAuth(secret[SECRET_FIELD_USERNAME], secret[SECRET_FIELD_PASSWORD], header_name)
        else:
            raise ValueError(ERROR_SECRET_MISSING_TOKEN_OR_CREDS)

        # Wrap with auto-refresh functionality
        cache_key = f"{self.provider_name}:{self._get_cache_key()}"
        return _AutoRefreshAuth(auth, self, cache_key)

    # Abstracts for concrete providers

    @abstractmethod
    def _fetch_secret(self) -> str | None:
        """Fetch the raw secret string from the backend.

        Implementations may return:
          * JSON-encoded material (auto-detected & parsed by `parse_secret_json`), or
          * Plain strings (token or "username:password").

        Returns:
            The raw secret string or None if unavailable.

        """
        raise NotImplementedError

    @abstractmethod
    def _get_cache_key(self) -> str:
        """Return a stable key that uniquely identifies the current secret configuration.

        This key is used for caching. It should reflect any input that would alter the
        resolved secret value (e.g., secret path/name, auth method, workspace).
        """
        raise NotImplementedError

    @abstractmethod
    def _get_auth_mode(self) -> AuthMode:
        """Return the authentication mode expected by this provider.

        Returns:
            Either "bearer" or "basic".

        """
        raise NotImplementedError

    @abstractmethod
    def _get_ttl(self) -> int:
        """Return cache TTL in seconds (must be positive).

        TTL is validated via `_validated_ttl` which gracefully falls back to `default_ttl`.
        """
        raise NotImplementedError


__all__ = [
    "AuthMode",
    "BasicAuth",
    "BearerAuth",
    "CustomHeaderAuth",
    "SecretData",
    "SecretsBackedAuthProvider",
]

"""HashiCorp Vault authentication provider."""

from __future__ import annotations

import json
import logging
from typing import Any

from mlflow_secrets_auth.base import SecretsBackedAuthProvider
from mlflow_secrets_auth.config import get_env_int, get_env_var
from mlflow_secrets_auth.utils import retry_with_jitter, safe_log, validate_ttl

from mlflow_secrets_auth.constants import (
    PROVIDER_VAULT,
    DEFAULT_TTL_SECONDS,
    ENV_VAULT_ADDR,
    ENV_VAULT_TOKEN,
    ENV_VAULT_ROLE_ID,
    ENV_VAULT_SECRET_ID,
    ENV_VAULT_SECRET_PATH,
    ENV_VAULT_AUTH_MODE,
    ENV_VAULT_TTL_SEC,
    DEFAULT_AUTH_MODE,
    VAULT_KV_V2_DATA_PREFIX,
    VAULT_KV_V1_PREFIX,
)

from mlflow_secrets_auth.messages import (
    ERROR_VAULT_HVAC_MISSING,
    INSTALL_VAULT,
    ERROR_VAULT_ADDR_MISSING,
    ERROR_VAULT_SECRET_PATH_MISSING,
    ERROR_VAULT_CREDS_MISSING,
    ERROR_VAULT_APPROLE_FAILED,
    ERROR_VAULT_AUTH_FAILED,
    LOG_VAULT_TOKEN_AUTH,
    LOG_VAULT_APPROLE_AUTH,
    LOG_VAULT_KV2_SUCCESS,
    LOG_VAULT_KV1_SUCCESS,
    LOG_VAULT_KV2_PATH,
    LOG_VAULT_KV1_PATH,
    LOG_VAULT_KV2_FALLBACK,
    LOG_VAULT_BOTH_KV_FAILED,
    LOG_VAULT_NO_SECRET_DATA,
)


class VaultAuthProvider(SecretsBackedAuthProvider):
    """Authentication provider using HashiCorp Vault.

    Supports token and AppRole authentication via the `hvac` client (optional dependency).
    Secrets are retrieved from KV v2 when possible with a graceful fallback to KV v1.

    Environment variables:
        VAULT_ADDR: Vault server address, e.g. "https://vault.example.com"
        VAULT_TOKEN: Vault token for direct authentication (optional).
        VAULT_ROLE_ID: AppRole role ID (used if VAULT_TOKEN is not provided).
        VAULT_SECRET_ID: AppRole secret ID (used if VAULT_TOKEN is not provided).
        MLFLOW_VAULT_SECRET_PATH: Secret path (e.g. "secret/mlflow/auth" or "secret/data/mlflow/auth").
        MLFLOW_VAULT_AUTH_MODE: "bearer" (default) or "basic".
        MLFLOW_VAULT_TTL_SEC: Cache TTL in seconds (defaults to provider's default TTL).

    Notes:
        * When using KV v2, this implementation auto-detects common path formats and
          reads via `client.secrets.kv.v2.read_secret_version`.
        * For KV v1, it falls back to `client.secrets.kv.v1.read_secret`.
        * Secret dictionaries are JSON-encoded for centralized parsing in the base class.

    """

    def __init__(self) -> None:
        """Initialize the provider with a default TTL and a lazy hvac client."""
        super().__init__(PROVIDER_VAULT, default_ttl=DEFAULT_TTL_SECONDS)
        self._vault_client: Any | None = None  # hvac.Client if available

    # Internal client management

    def _clear_client_cache(self) -> None:
        """Clear any cached Vault client instance."""
        self._vault_client = None

    def _get_vault_client(self) -> Any | None:
        """Return a cached or newly constructed hvac client.

        Returns:
            An authenticated `hvac.Client` instance, or None if unavailable/misconfigured.

        """
        if self._vault_client is not None:
            return self._vault_client

        try:
            import hvac  # type: ignore[import-untyped]
        except ImportError:
            safe_log(
                self.logger,
                logging.ERROR,
                f"{ERROR_VAULT_HVAC_MISSING} {INSTALL_VAULT}",
            )
            return None

        vault_addr = get_env_var(ENV_VAULT_ADDR)
        if not vault_addr:
            safe_log(self.logger, logging.DEBUG, ERROR_VAULT_ADDR_MISSING)
            return None

        client = hvac.Client(url=vault_addr)

        # Authenticate using token or AppRole
        vault_token = get_env_var(ENV_VAULT_TOKEN)
        if vault_token:
            client.token = vault_token
            safe_log(self.logger, logging.DEBUG, LOG_VAULT_TOKEN_AUTH)
        else:
            role_id = get_env_var(ENV_VAULT_ROLE_ID)
            secret_id = get_env_var(ENV_VAULT_SECRET_ID)

            if not role_id or not secret_id:
                safe_log(
                    self.logger,
                    logging.DEBUG,
                    ERROR_VAULT_CREDS_MISSING,
                )
                return None

            try:
                auth_response = client.auth.approle.login(role_id=role_id, secret_id=secret_id)
                client.token = auth_response["auth"]["client_token"]
                safe_log(self.logger, logging.DEBUG, LOG_VAULT_APPROLE_AUTH)
            except Exception as e:
                safe_log(self.logger, logging.DEBUG, ERROR_VAULT_APPROLE_FAILED.format(error=e))
                return None

        # Verify authentication
        if not client.is_authenticated():
            safe_log(self.logger, logging.DEBUG, ERROR_VAULT_AUTH_FAILED)
            return None

        self._vault_client = client
        return self._vault_client

    # SecretsBackedAuthProvider hooks

    def _fetch_secret(self) -> str | None:
        """Fetch raw secret material from Vault.

        Attempts KV v2 first (most common), then falls back to KV v1. Any retrieved
        dictionary is JSON-encoded before returning to the caller for centralized parsing.

        Returns:
            A JSON string with secret fields or None if retrieval fails.

        """
        secret_path = get_env_var(ENV_VAULT_SECRET_PATH)
        if not secret_path:
            safe_log(
                self.logger,
                logging.DEBUG,
                ERROR_VAULT_SECRET_PATH_MISSING,
            )
            return None

        client = self._get_vault_client()
        if client is None:
            return None

        def _fetch_from_vault() -> str | None:
            # Try KV v2 first
            try:
                # Normalize to KV v2 path "<mount>/data/<path>".
                if secret_path.startswith(VAULT_KV_V2_DATA_PREFIX):
                    kv2_path = secret_path
                elif secret_path.startswith(VAULT_KV_V1_PREFIX):
                    kv2_path = secret_path.replace(VAULT_KV_V1_PREFIX, VAULT_KV_V2_DATA_PREFIX, 1)
                else:
                    kv2_path = f"{VAULT_KV_V2_DATA_PREFIX}{secret_path.lstrip('/')}"

                safe_log(self.logger, logging.DEBUG, LOG_VAULT_KV2_PATH.format(path=kv2_path))

                # hvac v2 expects the path *relative* to the mount (strip "<mount>/data/")
                response = client.secrets.kv.v2.read_secret_version(
                    path=kv2_path.replace(VAULT_KV_V2_DATA_PREFIX, "", 1),
                )

                if response and "data" in response and "data" in response["data"]:
                    secret_data = response["data"]["data"]
                    safe_log(self.logger, logging.DEBUG, LOG_VAULT_KV2_SUCCESS)
                    return json.dumps(secret_data)

            except Exception as e:
                safe_log(self.logger, logging.DEBUG, LOG_VAULT_KV2_FALLBACK.format(error=e))

                # Fallback to KV v1
                try:
                    # Convert any v2-style path back to v1 for the fallback.
                    if secret_path.startswith(VAULT_KV_V2_DATA_PREFIX):
                        kv1_path = secret_path.replace(VAULT_KV_V2_DATA_PREFIX, VAULT_KV_V1_PREFIX, 1)
                    elif secret_path.startswith(VAULT_KV_V1_PREFIX):
                        kv1_path = secret_path
                    else:
                        kv1_path = f"{VAULT_KV_V1_PREFIX}{secret_path.lstrip('/')}"

                    safe_log(self.logger, logging.DEBUG, LOG_VAULT_KV1_PATH.format(path=kv1_path))

                    # hvac v1 expects the path *relative* to the mount (strip "<mount>/")
                    response = client.secrets.kv.v1.read_secret(
                        path=kv1_path.replace(VAULT_KV_V1_PREFIX, "", 1),
                    )

                    if response and "data" in response:
                        secret_data = response["data"]
                        safe_log(self.logger, logging.DEBUG, LOG_VAULT_KV1_SUCCESS)
                        return json.dumps(secret_data)

                except Exception as e2:
                    safe_log(self.logger, logging.ERROR, LOG_VAULT_BOTH_KV_FAILED.format(error=e2))
                    raise e2

            safe_log(self.logger, logging.WARNING, LOG_VAULT_NO_SECRET_DATA)
            return None

        try:
            return retry_with_jitter(_fetch_from_vault)
        except Exception:
            return None

    def _get_cache_key(self) -> str:
        """Return a cache key representing the current Vault configuration.

        Combines the Vault address and secret path so distinct configs cache independently.

        Returns:
            A unique key for the cache layer.

        """
        secret_path = get_env_var(ENV_VAULT_SECRET_PATH, "") or ""
        vault_addr = get_env_var(ENV_VAULT_ADDR, "") or ""
        return f"{vault_addr}:{secret_path}"

    def _get_auth_mode(self) -> str:
        """Return the authentication mode.

        Returns:
            "bearer" (default) or "basic", based on `MLFLOW_VAULT_AUTH_MODE`.

        """
        return (get_env_var(ENV_VAULT_AUTH_MODE, DEFAULT_AUTH_MODE) or DEFAULT_AUTH_MODE).lower()

    def _get_ttl(self) -> int:
        """Return the TTL (in seconds) for caching.

        Returns:
            Validated TTL (clamped) based on `MLFLOW_VAULT_TTL_SEC` or default.

        """
        ttl = get_env_int(ENV_VAULT_TTL_SEC, self.default_ttl)
        return validate_ttl(ttl)

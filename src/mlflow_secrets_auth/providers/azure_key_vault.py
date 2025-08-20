"""Azure Key Vault authentication provider."""

from __future__ import annotations

import logging
from typing import Any

from mlflow_secrets_auth.base import SecretsBackedAuthProvider
from mlflow_secrets_auth.config import get_env_int, get_env_var
from mlflow_secrets_auth.utils import retry_with_jitter, safe_log, validate_ttl

from mlflow_secrets_auth.constants import (
    PROVIDER_AZURE,
    DEFAULT_TTL_SECONDS,
    DEFAULT_AUTH_MODE,
    ENV_AZURE_VAULT_URL,
    ENV_AZURE_SECRET_NAME,
    ENV_AZURE_AUTH_MODE,
    ENV_AZURE_TTL_SEC,
)

from mlflow_secrets_auth.messages import (
    ERROR_AZURE_PACKAGES_MISSING,
    ERROR_AZURE_VAULT_URL_MISSING,
    ERROR_AZURE_URL_NOT_HTTPS,
    ERROR_AZURE_CLIENT_CREATE_FAILED,
    ERROR_AZURE_SECRET_NAME_MISSING,
    INSTALL_AZURE,
    LOG_AZURE_CLIENT_CREATED,
    LOG_AZURE_FETCHING_SECRET,
    LOG_AZURE_SECRET_SUCCESS,
    LOG_AZURE_SECRET_EMPTY,
    LOG_AZURE_FETCH_FAILED,
)


class AzureKeyVaultAuthProvider(SecretsBackedAuthProvider):
    """Authentication provider using Azure Key Vault.

    Requires optional dependencies: `azure-identity` and `azure-keyvault-secrets`.

    Environment variables:
        AZURE_KEY_VAULT_URL: Full Key Vault URL (e.g., "https://myvault.vault.azure.net"). Required.
        MLFLOW_AZURE_SECRET_NAME: Secret name to retrieve. Required.
        MLFLOW_AZURE_AUTH_MODE: "bearer" (default) or "basic".
        MLFLOW_AZURE_TTL_SEC: Cache TTL in seconds (defaults to provider's default TTL).
    """

    def __init__(self) -> None:
        """Initialize the provider with a default TTL and a lazy SecretClient."""
        super().__init__(PROVIDER_AZURE, default_ttl=DEFAULT_TTL_SECONDS)
        self._secret_client: Any | None = None  # azure.keyvault.secrets.SecretClient when available

    # Internal client management

    def _get_secret_client(self) -> Any:
        """Return a cached or newly constructed Azure Key Vault SecretClient.

        Returns:
            An authenticated `SecretClient`.

        Raises:
            ImportError: If required Azure packages are not installed.
            ValueError: If environment variables are missing or client creation fails.

        """
        if self._secret_client is not None:
            return self._secret_client

        try:
            from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]
            from azure.keyvault.secrets import SecretClient  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - optional dependency path
            msg = f"{ERROR_AZURE_PACKAGES_MISSING} {INSTALL_AZURE}"
            raise ImportError(msg) from exc

        vault_url = (get_env_var(ENV_AZURE_VAULT_URL) or "").strip()
        if not vault_url:
            raise ValueError(ERROR_AZURE_VAULT_URL_MISSING)
        if not vault_url.lower().startswith("https://"):
            raise ValueError(ERROR_AZURE_URL_NOT_HTTPS)

        try:
            credential = DefaultAzureCredential()
            self._secret_client = SecretClient(vault_url=vault_url, credential=credential)
            safe_log(self.logger, logging.DEBUG, LOG_AZURE_CLIENT_CREATED.format(url=vault_url))
            return self._secret_client
        except Exception as e:  # pragma: no cover — defensive
            msg = ERROR_AZURE_CLIENT_CREATE_FAILED.format(error=e)
            raise ValueError(msg) from e

    # SecretsBackedAuthProvider hooks

    def _fetch_secret(self) -> str | None:
        """Fetch the raw secret value from Azure Key Vault.

        Returns:
            Secret value as a string, or None if retrieval fails.

        Raises:
            ValueError: If required environment variables are missing.
            ImportError: If Azure SDK dependencies are not installed.

        """
        secret_name = (get_env_var(ENV_AZURE_SECRET_NAME) or "").strip()
        if not secret_name:
            raise ValueError(ERROR_AZURE_SECRET_NAME_MISSING)

        client = self._get_secret_client()

        def _fetch_from_azure() -> str | None:
            safe_log(self.logger, logging.DEBUG, LOG_AZURE_FETCHING_SECRET.format(name=secret_name))
            secret = client.get_secret(secret_name)

            if secret and getattr(secret, "value", None):
                safe_log(self.logger, logging.DEBUG, LOG_AZURE_SECRET_SUCCESS)
                return secret.value

            safe_log(self.logger, logging.WARNING, LOG_AZURE_SECRET_EMPTY.format(name=secret_name))
            return None

        try:
            return retry_with_jitter(_fetch_from_azure)
        except Exception as e:  # pragma: no cover — defensive
            safe_log(self.logger, logging.ERROR, LOG_AZURE_FETCH_FAILED.format(error=e))
            return None

    def _get_cache_key(self) -> str:
        """Return a cache key representing the current Azure configuration.

        Returns:
            "<vault_url>:<secret_name>" so distinct configs cache independently.

        """
        vault_url = (get_env_var(ENV_AZURE_VAULT_URL, "") or "").strip()
        secret_name = (get_env_var(ENV_AZURE_SECRET_NAME, "") or "").strip()
        return f"{vault_url}:{secret_name}"

    def _get_auth_mode(self) -> str:
        """Return the authentication mode.

        Returns:
            "bearer" (default) or "basic", based on `MLFLOW_AZURE_AUTH_MODE`.

        """
        return (get_env_var(ENV_AZURE_AUTH_MODE, DEFAULT_AUTH_MODE) or DEFAULT_AUTH_MODE).lower()

    def _get_ttl(self) -> int:
        """Return the TTL (in seconds) for caching.

        Returns:
            Validated TTL (clamped) based on `MLFLOW_AZURE_TTL_SEC` or default.

        """
        ttl = get_env_int(ENV_AZURE_TTL_SEC, self.default_ttl)
        return validate_ttl(ttl)

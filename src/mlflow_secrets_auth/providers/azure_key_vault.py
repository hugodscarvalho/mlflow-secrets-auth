"""Azure Key Vault authentication provider."""

from __future__ import annotations

import logging
from typing import Any

from mlflow_secrets_auth.base import SecretsBackedAuthProvider
from mlflow_secrets_auth.config import get_env_int, get_env_var
from mlflow_secrets_auth.utils import retry_with_jitter, safe_log, validate_ttl


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
        super().__init__("azure-key-vault", default_ttl=300)
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
            from azure.identity import DefaultAzureCredential  # type: ignore
            from azure.keyvault.secrets import SecretClient  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency path
            msg = (
                "azure-identity and azure-keyvault-secrets packages are required "
                "for Azure Key Vault support. "
                "Install with: pip install mlflow-secrets-auth[azure]"
            )
            raise ImportError(msg) from exc

        vault_url = (get_env_var("AZURE_KEY_VAULT_URL") or "").strip()
        if not vault_url:
            msg = "AZURE_KEY_VAULT_URL environment variable is required"
            raise ValueError(msg)
        if not vault_url.lower().startswith("https://"):
            msg = "AZURE_KEY_VAULT_URL must start with https://"
            raise ValueError(msg)

        try:
            credential = DefaultAzureCredential()
            self._secret_client = SecretClient(vault_url=vault_url, credential=credential)
            safe_log(self.logger, logging.DEBUG, "Created Azure Key Vault client for %s", vault_url)
            return self._secret_client
        except Exception as e:  # pragma: no cover — defensive
            msg = f"Failed to create Azure Key Vault client: {e}"
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
        secret_name = (get_env_var("MLFLOW_AZURE_SECRET_NAME") or "").strip()
        if not secret_name:
            msg = "MLFLOW_AZURE_SECRET_NAME environment variable is required"
            raise ValueError(msg)

        client = self._get_secret_client()

        def _fetch_from_azure() -> str | None:
            safe_log(self.logger, logging.DEBUG, "Fetching secret: %s", secret_name)
            secret = client.get_secret(secret_name)

            if secret and getattr(secret, "value", None):
                safe_log(self.logger, logging.DEBUG, "Successfully fetched secret from Azure Key Vault")
                return secret.value

            safe_log(self.logger, logging.WARNING, "Secret value is empty for %s", secret_name)
            return None

        try:
            return retry_with_jitter(_fetch_from_azure)
        except Exception as e:  # pragma: no cover — defensive
            safe_log(self.logger, logging.ERROR, "Failed to fetch secret from Azure Key Vault: %s", e)
            return None

    def _get_cache_key(self) -> str:
        """Return a cache key representing the current Azure configuration.

        Returns:
            "<vault_url>:<secret_name>" so distinct configs cache independently.

        """
        vault_url = (get_env_var("AZURE_KEY_VAULT_URL", "") or "").strip()
        secret_name = (get_env_var("MLFLOW_AZURE_SECRET_NAME", "") or "").strip()
        return f"{vault_url}:{secret_name}"

    def _get_auth_mode(self) -> str:
        """Return the authentication mode.

        Returns:
            "bearer" (default) or "basic", based on `MLFLOW_AZURE_AUTH_MODE`.

        """
        return (get_env_var("MLFLOW_AZURE_AUTH_MODE", "bearer") or "bearer").lower()

    def _get_ttl(self) -> int:
        """Return the TTL (in seconds) for caching.

        Returns:
            Validated TTL (clamped) based on `MLFLOW_AZURE_TTL_SEC` or default.

        """
        ttl = get_env_int("MLFLOW_AZURE_TTL_SEC", self.default_ttl)
        return validate_ttl(ttl)

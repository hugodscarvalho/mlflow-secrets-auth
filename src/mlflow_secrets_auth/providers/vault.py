"""HashiCorp Vault authentication provider."""

from __future__ import annotations

import json
import logging
from typing import Any

from mlflow_secrets_auth.base import SecretsBackedAuthProvider
from mlflow_secrets_auth.config import get_env_int, get_env_var
from mlflow_secrets_auth.utils import retry_with_jitter, safe_log, validate_ttl


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
        super().__init__("vault", default_ttl=300)
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
            import hvac  # type: ignore
        except ImportError:
            safe_log(
                self.logger,
                logging.ERROR,
                "hvac package is required for Vault support. "
                "Install with: pip install mlflow-secrets-auth[vault]",
            )
            return None

        vault_addr = get_env_var("VAULT_ADDR")
        if not vault_addr:
            safe_log(self.logger, logging.DEBUG, "VAULT_ADDR environment variable is required")
            return None

        client = hvac.Client(url=vault_addr)

        # Authenticate using token or AppRole
        vault_token = get_env_var("VAULT_TOKEN")
        if vault_token:
            client.token = vault_token
            safe_log(self.logger, logging.DEBUG, "Using Vault token authentication")
        else:
            role_id = get_env_var("VAULT_ROLE_ID")
            secret_id = get_env_var("VAULT_SECRET_ID")

            if not role_id or not secret_id:
                safe_log(
                    self.logger,
                    logging.DEBUG,
                    "Either VAULT_TOKEN or both VAULT_ROLE_ID and VAULT_SECRET_ID "
                    "environment variables are required",
                )
                return None

            try:
                auth_response = client.auth.approle.login(role_id=role_id, secret_id=secret_id)
                client.token = auth_response["auth"]["client_token"]
                safe_log(self.logger, logging.DEBUG, "Using Vault AppRole authentication")
            except Exception as e:
                safe_log(self.logger, logging.DEBUG, f"Vault AppRole authentication failed: {e}")
                return None

        # Verify authentication
        if not client.is_authenticated():
            safe_log(self.logger, logging.DEBUG, "Vault authentication failed")
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
        secret_path = get_env_var("MLFLOW_VAULT_SECRET_PATH")
        if not secret_path:
            safe_log(
                self.logger,
                logging.DEBUG,
                "MLFLOW_VAULT_SECRET_PATH environment variable is required",
            )
            return None

        client = self._get_vault_client()
        if client is None:
            return None

        def _fetch_from_vault() -> str | None:
            # Try KV v2
            try:
                # Normalize to kv2 path "secret/data/<path>" but hvac.v2.read_secret_version
                # expects the path relative to mount point, so we strip "secret/data/" again.
                if not secret_path.startswith("secret/data/"):
                    kv2_path = secret_path.replace("secret/", "secret/data/", 1) if secret_path.startswith("secret/") else f"secret/data/{secret_path}"
                else:
                    kv2_path = secret_path

                safe_log(self.logger, logging.DEBUG, f"Trying KV v2 path: {kv2_path}")
                response = client.secrets.kv.v2.read_secret_version(path=kv2_path.replace("secret/data/", ""))

                if response and "data" in response and "data" in response["data"]:
                    secret_data = response["data"]["data"]
                    safe_log(self.logger, logging.DEBUG, "Successfully fetched secret using KV v2")
                    return json.dumps(secret_data)

            except Exception as e:
                safe_log(self.logger, logging.DEBUG, f"KV v2 failed, trying KV v1: {e}")

                # Fallback to KV v1
                try:
                    kv1_path = secret_path.replace("secret/data/", "secret/")
                    safe_log(self.logger, logging.DEBUG, f"Trying KV v1 path: {kv1_path}")
                    response = client.secrets.kv.v1.read_secret(path=kv1_path.replace("secret/", ""))

                    if response and "data" in response:
                        secret_data = response["data"]
                        safe_log(self.logger, logging.DEBUG, "Successfully fetched secret using KV v1")
                        return json.dumps(secret_data)

                except Exception as e2:
                    safe_log(self.logger, logging.ERROR, f"Both KV v1 and v2 failed: {e2}")
                    raise e2

            safe_log(self.logger, logging.WARNING, "No secret data found at path")
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
        secret_path = get_env_var("MLFLOW_VAULT_SECRET_PATH", "") or ""
        vault_addr = get_env_var("VAULT_ADDR", "") or ""
        return f"{vault_addr}:{secret_path}"

    def _get_auth_mode(self) -> str:
        """Return the authentication mode.

        Returns:
            "bearer" (default) or "basic", based on `MLFLOW_VAULT_AUTH_MODE`.

        """
        return (get_env_var("MLFLOW_VAULT_AUTH_MODE", "bearer") or "bearer").lower()

    def _get_ttl(self) -> int:
        """Return the TTL (in seconds) for caching.

        Returns:
            Validated TTL (clamped) based on `MLFLOW_VAULT_TTL_SEC` or default.

        """
        ttl = get_env_int("MLFLOW_VAULT_TTL_SEC", self.default_ttl)
        return validate_ttl(ttl)

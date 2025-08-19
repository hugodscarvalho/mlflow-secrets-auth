"""AWS Secrets Manager authentication provider."""

from __future__ import annotations

import base64
import logging
from typing import Any

from mlflow_secrets_auth.base import SecretsBackedAuthProvider
from mlflow_secrets_auth.config import get_env_int, get_env_var
from mlflow_secrets_auth.utils import retry_with_jitter, safe_log, validate_ttl


class AWSSecretsManagerAuthProvider(SecretsBackedAuthProvider):
    """Authentication provider using AWS Secrets Manager.

    Requires the optional dependency `boto3`.

    Environment variables:
        AWS_REGION: AWS region (e.g., "eu-west-1"). Required.
        MLFLOW_AWS_SECRET_ID: Secret identifier or ARN. Required.
        MLFLOW_AWS_AUTH_MODE: "bearer" (default) or "basic".
        MLFLOW_AWS_TTL_SEC: Cache TTL in seconds (defaults to provider's default TTL).
    """

    def __init__(self) -> None:
        """Initialize the provider with a default TTL and lazy AWS client."""
        super().__init__("aws-secrets-manager", default_ttl=300)
        self._secrets_client: Any | None = None  # boto3 client when available

    # Internal client management

    def _get_secrets_client(self) -> Any:
        """Return a cached or newly constructed AWS Secrets Manager client.

        Returns:
            A boto3 `secretsmanager` client.

        Raises:
            ImportError: When `boto3` is not installed.
            ValueError: When required environment variables are missing or client creation fails.

        """
        if self._secrets_client is not None:
            return self._secrets_client

        try:
            import boto3  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dep path
            msg = (
                "boto3 package is required for AWS Secrets Manager support. "
                "Install with: pip install mlflow-secrets-auth[aws]"
            )
            raise ImportError(msg) from exc

        region = get_env_var("AWS_REGION")
        if not region:
            msg = "AWS_REGION environment variable is required"
            raise ValueError(msg)

        try:
            self._secrets_client = boto3.client("secretsmanager", region_name=region)
            safe_log(
                self.logger,
                logging.DEBUG,
                "Created AWS Secrets Manager client for region %s",
                region,
            )
            return self._secrets_client
        except Exception as e:  # pragma: no cover — defensive
            msg = f"Failed to create AWS Secrets Manager client: {e}"
            raise ValueError(msg) from e

    # SecretsBackedAuthProvider hooks

    def _fetch_secret(self) -> str | None:
        """Fetch the raw secret from AWS Secrets Manager.

        Tries `SecretString` first and falls back to base64-decoded `SecretBinary`.

        Returns:
            The secret value as a UTF-8 string, or None on failure.

        Raises:
            ValueError: If required environment variables are missing.
            ImportError: If `boto3` is not installed.

        """
        secret_id = get_env_var("MLFLOW_AWS_SECRET_ID")
        if not secret_id:
            msg = "MLFLOW_AWS_SECRET_ID environment variable is required"
            raise ValueError(msg)

        client = self._get_secrets_client()

        def _fetch_from_aws() -> str | None:
            safe_log(self.logger, logging.DEBUG, "Fetching secret: %s", secret_id)
            response = client.get_secret_value(SecretId=secret_id)

            if "SecretString" in response and response["SecretString"] is not None:
                secret_value = response["SecretString"]
                safe_log(
                    self.logger,
                    logging.DEBUG,
                    "Successfully fetched secret from AWS Secrets Manager",
                )
                return secret_value

            if "SecretBinary" in response and response["SecretBinary"] is not None:
                # Handle binary secrets
                secret_value = base64.b64decode(response["SecretBinary"]).decode("utf-8")
                safe_log(
                    self.logger,
                    logging.DEBUG,
                    "Successfully fetched binary secret from AWS Secrets Manager",
                )
                return secret_value

            safe_log(
                self.logger,
                logging.WARNING,
                "No SecretString or SecretBinary found in response for %s",
                secret_id,
            )
            return None

        try:
            return retry_with_jitter(_fetch_from_aws)
        except Exception as e:  # pragma: no cover — defensive
            safe_log(
                self.logger,
                logging.ERROR,
                "Failed to fetch secret from AWS Secrets Manager: %s",
                e,
            )
            return None

    def _get_cache_key(self) -> str:
        """Return a cache key representing the current AWS configuration.

        Returns:
            "<region>:<secret_id>" so distinct configs cache independently.

        """
        secret_id = get_env_var("MLFLOW_AWS_SECRET_ID", "") or ""
        region = get_env_var("AWS_REGION", "") or ""
        return f"{region}:{secret_id}"

    def _get_auth_mode(self) -> str:
        """Return the authentication mode.

        Returns:
            "bearer" (default) or "basic", based on `MLFLOW_AWS_AUTH_MODE`.

        """
        return (get_env_var("MLFLOW_AWS_AUTH_MODE", "bearer") or "bearer").lower()

    def _get_ttl(self) -> int:
        """Return the TTL (in seconds) for caching.

        Returns:
            Validated TTL (clamped) based on `MLFLOW_AWS_TTL_SEC` or default.

        """
        ttl = get_env_int("MLFLOW_AWS_TTL_SEC", self.default_ttl)
        return validate_ttl(ttl)

"""AWS Secrets Manager authentication provider."""

from __future__ import annotations

import base64
import logging
from typing import Any

from mlflow_secrets_auth.base import SecretsBackedAuthProvider
from mlflow_secrets_auth.config import get_env_int, get_env_var
from mlflow_secrets_auth.utils import retry_with_jitter, safe_log, validate_ttl

from mlflow_secrets_auth.constants import (
    PROVIDER_AWS,
    DEFAULT_TTL_SECONDS,
    DEFAULT_AUTH_MODE,
    ENV_AWS_REGION,
    ENV_AWS_SECRET_ID,
    ENV_AWS_AUTH_MODE,
    ENV_AWS_TTL_SEC,
)

from mlflow_secrets_auth.messages import (
    ERROR_AWS_BOTO3_MISSING,
    ERROR_AWS_REGION_MISSING,
    ERROR_AWS_SECRET_ID_MISSING,
    ERROR_AWS_CLIENT_CREATION,
    LOG_AWS_CLIENT_CREATED,
    LOG_AWS_FETCHING_SECRET,
    LOG_AWS_SECRET_STRING_SUCCESS,
    LOG_AWS_SECRET_BINARY_SUCCESS,
    LOG_AWS_NO_SECRET_DATA,
    LOG_AWS_FETCH_FAILED,
)


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
        super().__init__(PROVIDER_AWS, default_ttl=DEFAULT_TTL_SECONDS)
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
            import boto3  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - optional dep path
            msg = ERROR_AWS_BOTO3_MISSING
            raise ImportError(msg) from exc

        region = get_env_var(ENV_AWS_REGION)
        if not region:
            msg = ERROR_AWS_REGION_MISSING
            raise ValueError(msg)

        try:
            self._secrets_client = boto3.client("secretsmanager", region_name=region)
            safe_log(self.logger, logging.DEBUG, LOG_AWS_CLIENT_CREATED.format(region=region))
            return self._secrets_client
        except Exception as e:  # pragma: no cover — defensive
            raise ValueError(ERROR_AWS_CLIENT_CREATION.format(error=e)) from e

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
        secret_id = get_env_var(ENV_AWS_SECRET_ID)
        if not secret_id:
            raise ValueError(ERROR_AWS_SECRET_ID_MISSING)

        client = self._get_secrets_client()

        def _fetch_from_aws() -> str | None:
            safe_log(self.logger, logging.DEBUG, LOG_AWS_FETCHING_SECRET.format(secret_id=secret_id))
            response = client.get_secret_value(SecretId=secret_id)

            if "SecretString" in response and response["SecretString"] is not None:
                secret_value = response["SecretString"]
                safe_log(self.logger, logging.DEBUG, LOG_AWS_SECRET_STRING_SUCCESS)
                return secret_value

            if "SecretBinary" in response and response["SecretBinary"] is not None:
                # Handle binary secrets
                secret_value = base64.b64decode(response["SecretBinary"]).decode("utf-8")
                safe_log(self.logger, logging.DEBUG, LOG_AWS_SECRET_BINARY_SUCCESS)
                return secret_value

            safe_log(self.logger, logging.WARNING, LOG_AWS_NO_SECRET_DATA.format(secret_id=secret_id))
            return None

        try:
            return retry_with_jitter(_fetch_from_aws)
        except Exception as e:  # pragma: no cover — defensive
            safe_log(self.logger, logging.ERROR, LOG_AWS_FETCH_FAILED.format(error=e))
            return None

    def _get_cache_key(self) -> str:
        """Return a cache key representing the current AWS configuration.

        Returns:
            "<region>:<secret_id>" so distinct configs cache independently.

        """
        secret_id = get_env_var(ENV_AWS_SECRET_ID, "") or ""
        region = get_env_var(ENV_AWS_REGION, "") or ""
        return f"{region}:{secret_id}"

    def _get_auth_mode(self) -> str:
        """Return the authentication mode.

        Returns:
            "bearer" (default) or "basic", based on `MLFLOW_AWS_AUTH_MODE`.

        """
        return (get_env_var(ENV_AWS_AUTH_MODE, DEFAULT_AUTH_MODE) or DEFAULT_AUTH_MODE).lower()

    def _get_ttl(self) -> int:
        """Return the TTL (in seconds) for caching.

        Returns:
            Validated TTL (clamped) based on `MLFLOW_AWS_TTL_SEC` or default.

        """
        ttl = get_env_int(ENV_AWS_TTL_SEC, self.default_ttl)
        return validate_ttl(ttl)

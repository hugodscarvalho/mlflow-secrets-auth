"""Constants for MLflow Secrets Auth.

This module centralizes all configuration constants, environment variable names,
default values, and magic strings used throughout the project.
"""

from __future__ import annotations

from typing import Final

# =============================================================================
# Environment Variable Names
# =============================================================================

# Core configuration
ENV_ALLOWED_HOSTS: Final[str] = "MLFLOW_SECRETS_ALLOWED_HOSTS"
ENV_AUTH_HEADER_NAME: Final[str] = "MLFLOW_AUTH_HEADER_NAME"
ENV_LOG_LEVEL: Final[str] = "MLFLOW_SECRETS_LOG_LEVEL"
ENV_AUTH_ENABLE: Final[str] = "MLFLOW_SECRETS_AUTH_ENABLE"

# Environment variable prefixes
ENV_AUTH_ENABLE_PREFIX = "MLFLOW_SECRETS_AUTH_ENABLE_"

# Vault provider
ENV_VAULT_ADDR: Final[str] = "VAULT_ADDR"
ENV_VAULT_TOKEN: Final[str] = "VAULT_TOKEN"
ENV_VAULT_ROLE_ID: Final[str] = "VAULT_ROLE_ID"
ENV_VAULT_SECRET_ID: Final[str] = "VAULT_SECRET_ID"
ENV_VAULT_SECRET_PATH: Final[str] = "MLFLOW_VAULT_SECRET_PATH"
ENV_VAULT_AUTH_MODE: Final[str] = "MLFLOW_VAULT_AUTH_MODE"
ENV_VAULT_TTL_SEC: Final[str] = "MLFLOW_VAULT_TTL_SEC"

# AWS provider
ENV_AWS_REGION: Final[str] = "AWS_REGION"
ENV_AWS_SECRET_ID: Final[str] = "MLFLOW_AWS_SECRET_ID"
ENV_AWS_AUTH_MODE: Final[str] = "MLFLOW_AWS_AUTH_MODE"
ENV_AWS_TTL_SEC: Final[str] = "MLFLOW_AWS_TTL_SEC"

# Azure provider
ENV_AZURE_VAULT_URL: Final[str] = "AZURE_KEY_VAULT_URL"
ENV_AZURE_SECRET_NAME: Final[str] = "MLFLOW_AZURE_SECRET_NAME"
ENV_AZURE_AUTH_MODE: Final[str] = "MLFLOW_AZURE_AUTH_MODE"
ENV_AZURE_TTL_SEC: Final[str] = "MLFLOW_AZURE_TTL_SEC"

# =============================================================================
# Default Values
# =============================================================================

DEFAULT_TTL_SECONDS: Final[int] = 300
DEFAULT_AUTH_MODE: Final[str] = "bearer"
DEFAULT_AUTH_HEADER: Final[str] = "Authorization"
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
DEFAULT_REQUEST_TIMEOUT: Final[int] = 10
DEFAULT_CACHE_SIZE: Final[int] = 0
DEFAULT_MASK_CHAR: Final[str] = "*"
DEFAULT_SHOW_CHARS: Final[int] = 4

# =============================================================================
# Authentication Modes
# =============================================================================

AUTH_MODE_BEARER: Final[str] = "bearer"
AUTH_MODE_BASIC: Final[str] = "basic"
VALID_AUTH_MODES: Final[tuple[str, ...]] = (AUTH_MODE_BEARER, AUTH_MODE_BASIC)

# =============================================================================
# Secret Field Names
# =============================================================================

SECRET_FIELD_TOKEN: Final[str] = "token"
SECRET_FIELD_USERNAME: Final[str] = "username"
SECRET_FIELD_PASSWORD: Final[str] = "password"

# =============================================================================
# Provider Names
# =============================================================================

PROVIDER_VAULT: Final[str] = "vault"
PROVIDER_AWS: Final[str] = "aws-secrets-manager"
PROVIDER_AZURE: Final[str] = "azure-key-vault"
ALL_PROVIDERS: Final[tuple[str, ...]] = (PROVIDER_VAULT, PROVIDER_AWS, PROVIDER_AZURE)

# =============================================================================
# HTTP Headers
# =============================================================================

HEADER_AUTHORIZATION: Final[str] = "Authorization"
HEADER_RETRY_MARKER: Final[str] = "X-MLFSA-Retried"
HEADER_RETRY_VALUE: Final[str] = "true"

# =============================================================================
# Package Names (for install instructions)
# =============================================================================

PACKAGE_NAME: Final[str] = "mlflow-secrets-auth"
PACKAGE_HVAC: Final[str] = "hvac"
PACKAGE_BOTO3: Final[str] = "boto3"
PACKAGE_AZURE_IDENTITY: Final[str] = "azure-identity"
PACKAGE_AZURE_KEYVAULT: Final[str] = "azure-keyvault-secrets"

# =============================================================================
# Boolean Environment Values
# =============================================================================

TRUTHY_VALUES: Final[set[str]] = {"1", "true", "yes", "on"}

# =============================================================================
# Vault-specific Constants
# =============================================================================

VAULT_KV_V2_DATA_PREFIX: Final[str] = "secret/data/"
VAULT_KV_V1_PREFIX: Final[str] = "secret/"

# =============================================================================
# Regex and Validation
# =============================================================================

MIN_TTL_SECONDS: Final[int] = 1
MAX_TTL_SECONDS: Final[int] = 86400  # 24 hours

# =============================================================================
# CLI Constants
# =============================================================================

CLI_COMMAND_INFO: Final[str] = "info"
CLI_COMMAND_DOCTOR: Final[str] = "doctor"
CLI_ARG_DRY_RUN: Final[str] = "--dry-run"

EXIT_SUCCESS: Final[int] = 0
EXIT_ERROR: Final[int] = 1

"""User-facing messages for MLflow Secrets Auth.

This module centralizes all user-facing messages including CLI output,
error messages, log messages, and help text.
"""

from __future__ import annotations

from typing import Final

# =============================================================================
# CLI Messages
# =============================================================================

# Headers
CLI_HEADER_INFO: Final[str] = "MLflow Secrets Auth - Info"
CLI_HEADER_DOCTOR: Final[str] = "MLflow Secrets Auth - Doctor"

# Status indicators
STATUS_SUCCESS: Final[str] = "✅"
STATUS_ERROR: Final[str] = "❌"
STATUS_TESTING: Final[str] = "🔍"
STATUS_WARNING: Final[str] = "⚠️"
STATUS_CELEBRATION: Final[str] = "🎉"

# CLI help text
CLI_DESCRIPTION: Final[str] = "MLflow Secrets Auth CLI"
CLI_HELP_COMMANDS: Final[str] = "Available commands"
CLI_HELP_DOCTOR: Final[str] = "Run diagnostics"
CLI_HELP_INFO: Final[str] = "Show plugin information and configuration"
CLI_HELP_DRY_RUN: Final[str] = "Test auth against specified MLflow tracking URL"

# Info command messages
INFO_VERSION: Final[str] = "Version: {version}"
INFO_VERSION_DEV: Final[str] = "Version: Development/Editable install"
INFO_VERSION_UNKNOWN: Final[str] = "Version: Unknown"
INFO_ENABLED_PROVIDERS: Final[str] = "Enabled providers: {providers}"
INFO_NO_ENABLED_PROVIDERS: Final[str] = "Enabled providers: None"
INFO_DISABLED_PROVIDERS: Final[str] = "Available but disabled providers: {providers}"
INFO_ALLOWED_HOSTS: Final[str] = "Allowed hosts: {hosts}"
INFO_ALL_HOSTS_ALLOWED: Final[str] = "Allowed hosts: All hosts allowed"
INFO_AUTH_HEADER: Final[str] = "Auth header name: {header}"
INFO_CACHE_SIZE: Final[str] = "Cache size: {size}"

# Doctor command messages
DOCTOR_NO_PROVIDER: Final[str] = "No enabled provider found"
DOCTOR_NO_PROVIDERS_ENABLED: Final[str] = "No providers are currently enabled in configuration"
DOCTOR_AVAILABLE_PROVIDERS: Final[str] = "Available providers: {providers}"
DOCTOR_FOUND_ENABLED: Final[str] = "Found enabled providers: {providers}"
DOCTOR_INIT_FAILED: Final[str] = "But failed to initialize provider instance"
DOCTOR_PROVIDER_OK: Final[str] = "Provider: {provider}"
DOCTOR_AUTH_MODE_OK: Final[str] = "Auth mode: {mode}"
DOCTOR_AUTH_HEADER_OK: Final[str] = "Auth header: {header}"
DOCTOR_TTL_OK: Final[str] = "TTL: {ttl} seconds"
DOCTOR_CACHE_SIZE_OK: Final[str] = "Cache size: {size}"
DOCTOR_ALLOWED_HOSTS_OK: Final[str] = "Allowed hosts: {hosts}"
DOCTOR_ALL_HOSTS_OK: Final[str] = "Allowed hosts: All hosts allowed"
DOCTOR_CONFIG_ERROR: Final[str] = "Configuration error: {error}"
DOCTOR_TESTING_SECRET_FETCH: Final[str] = "Testing secret fetch..."
DOCTOR_SECRET_FETCH_FAILED: Final[str] = "Failed to fetch secret data"
DOCTOR_SECRET_FETCH_OK: Final[str] = "Secret fetched successfully"
DOCTOR_TESTING_AUTH_CONSTRUCTION: Final[str] = "Testing auth construction..."
DOCTOR_AUTH_CONSTRUCTION_OK: Final[str] = "Auth object created successfully"
DOCTOR_AUTH_TYPE: Final[str] = "Auth type: {auth_type}"
DOCTOR_AUTH_CONSTRUCTION_FAILED: Final[str] = "Failed to create auth object: {error}"
DOCTOR_SECRET_FETCH_ERROR: Final[str] = "Secret fetch failed: {error}"
DOCTOR_DRY_RUN_TESTING: Final[str] = "Testing dry-run against: {url}"
DOCTOR_INVALID_URL: Final[str] = "Invalid URL format"
DOCTOR_HOST_NOT_ALLOWED: Final[str] = "Host {host} not in allowed hosts: {allowed_hosts}"
DOCTOR_NO_AUTH_FOR_URL: Final[str] = "No auth returned for URL"
DOCTOR_MAKING_REQUEST: Final[str] = "Making HEAD request to: {origin}"
DOCTOR_REQUEST_SUCCESS: Final[str] = "Request successful - Status: {status_code}"
DOCTOR_REQUEST_FAILED: Final[str] = "Request failed (this may be normal): {error}"
DOCTOR_DRY_RUN_FAILED: Final[str] = "Dry-run test failed: {error}"
DOCTOR_ALL_PASSED: Final[str] = "All diagnostics passed!"

# =============================================================================
# Error Messages
# =============================================================================

# Secret validation errors
ERROR_SECRET_EMPTY: Final[str] = "Secret is empty"
ERROR_SECRET_INVALID_JSON: Final[str] = "Secret value must be a JSON object"
ERROR_SECRET_TOKEN_INVALID: Final[str] = "Secret 'token' field must be a non-empty string"
ERROR_SECRET_USERNAME_INVALID: Final[str] = "Secret 'username' field must be a non-empty string"
ERROR_SECRET_PASSWORD_INVALID: Final[str] = "Secret 'password' field must be a non-empty string"
ERROR_SECRET_MISSING_FIELDS: Final[str] = "Secret must contain either 'token' field or both 'username' and 'password' fields"
ERROR_SECRET_MISSING_TOKEN_OR_CREDS: Final[str] = "Secret data must contain 'token' or 'username' + 'password'."

# Auth mode / format validation
ERROR_BASIC_TOKEN_FORMAT: Final[str] = "Basic auth requires token formatted as 'username:password'."
ERROR_BEARER_WITH_USERPASS: Final[str] = "Bearer mode does not accept username/password secrets."

# Provider-specific errors
ERROR_AWS_BOTO3_MISSING: Final[str] = (
    "boto3 package is required for AWS Secrets Manager support. "
    "Install with: pip install mlflow-secrets-auth[aws]"
)
ERROR_AWS_REGION_MISSING: Final[str] = "AWS_REGION environment variable is required"
ERROR_AWS_SECRET_ID_MISSING: Final[str] = "MLFLOW_AWS_SECRET_ID environment variable is required"
ERROR_AWS_CLIENT_CREATION: Final[str] = "Failed to create AWS Secrets Manager client: {error}"

ERROR_VAULT_HVAC_MISSING: Final[str] = (
    "hvac package is required for Vault support. "
    "Install with: pip install mlflow-secrets-auth[vault]"
)
ERROR_VAULT_ADDR_MISSING: Final[str] = "VAULT_ADDR environment variable is required"
ERROR_VAULT_SECRET_PATH_MISSING: Final[str] = "MLFLOW_VAULT_SECRET_PATH environment variable is required"
ERROR_VAULT_CREDS_MISSING: Final[str] = (
    "Either VAULT_TOKEN or both VAULT_ROLE_ID and VAULT_SECRET_ID "
    "environment variables are required"
)
ERROR_VAULT_APPROLE_FAILED: Final[str] = "Vault AppRole authentication failed: {error}"
ERROR_VAULT_AUTH_FAILED: Final[str] = "Vault authentication failed"

ERROR_AZURE_PACKAGES_MISSING: Final[str] = (
    "azure-identity and azure-keyvault-secrets packages are required for Azure Key Vault support. "
    "Install with: pip install mlflow-secrets-auth[azure]"
)
ERROR_AZURE_VAULT_URL_MISSING: Final[str] = "AZURE_KEY_VAULT_URL environment variable is required"
ERROR_AZURE_SECRET_NAME_MISSING: Final[str] = "MLFLOW_AZURE_SECRET_NAME environment variable is required"
ERROR_AZURE_URL_NOT_HTTPS: Final[str] = "AZURE_KEY_VAULT_URL must start with https://"
ERROR_AZURE_CLIENT_CREATE_FAILED: Final[str] = "Failed to create Azure Key Vault client: {error}"

# =============================================================================
# Providers / Runtime Messages
# =============================================================================

# Provider status / generic errors
DEBUG_PROVIDER_NOT_ENABLED: Final[str] = "{provider} provider not enabled"
ERROR_UNEXPECTED_PROVIDER: Final[str] = "Unexpected error in {provider}: {error}"
INFO_HOST_NOT_ALLOWED: Final[str] = "Host {hostname} not in allowed hosts list; skipping auth"
WARNING_FETCH_FAILED: Final[str] = "Failed to fetch secret from {provider}"
WARNING_CONFIG_ERROR: Final[str] = "{provider} config error: {error}"
WARNING_INVALID_TTL: Final[str] = "Invalid TTL '{raw}'; falling back to default {default}"

# Auth refresh / retry flow
ERROR_REFRESH_FAILED: Final[str] = "Failed to refresh credentials after {status_code} response"
INFO_RETRYING_REQUEST: Final[str] = "Retrying request with fresh credentials after {status_code} response"
INFO_RETRY_COMPLETED: Final[str] = "Retry completed with status {status_code}"
ERROR_REFRESH_AND_RETRY: Final[str] = "Failed to refresh credentials and retry: {error}"

# =============================================================================
# Log Messages
# =============================================================================

# Debug messages
LOG_VAULT_TOKEN_AUTH: Final[str] = "Using Vault token authentication"
LOG_VAULT_APPROLE_AUTH: Final[str] = "Using Vault AppRole authentication"
LOG_VAULT_KV2_SUCCESS: Final[str] = "Successfully fetched secret using KV v2"
LOG_VAULT_KV1_SUCCESS: Final[str] = "Successfully fetched secret using KV v1"
LOG_VAULT_KV2_PATH: Final[str] = "Trying KV v2 path: {path}"
LOG_VAULT_KV1_PATH: Final[str] = "Trying KV v1 path: {path}"
LOG_VAULT_KV2_FALLBACK: Final[str] = "KV v2 failed, trying KV v1: {error}"

LOG_AWS_CLIENT_CREATED: Final[str] = "Created AWS Secrets Manager client for region {region}"
LOG_AWS_FETCHING_SECRET: Final[str] = "Fetching secret: {secret_id}"
LOG_AWS_SECRET_STRING_SUCCESS: Final[str] = "Successfully fetched secret from AWS Secrets Manager"
LOG_AWS_SECRET_BINARY_SUCCESS: Final[str] = "Successfully fetched binary secret from AWS Secrets Manager"

LOG_AZURE_CLIENT_CREATED: Final[str] = "Created Azure Key Vault client for {url}"
LOG_AZURE_FETCHING_SECRET: Final[str] = "Fetching secret: {name}"
LOG_AZURE_SECRET_SUCCESS: Final[str] = "Successfully fetched secret from Azure Key Vault"
LOG_AZURE_SECRET_EMPTY: Final[str] = "Secret value is empty for {name}"
LOG_AZURE_FETCH_FAILED: Final[str] = "Failed to fetch secret from Azure Key Vault: {error}"

# Warning messages
LOG_VAULT_NO_SECRET_DATA: Final[str] = "No secret data found at path"
LOG_AWS_NO_SECRET_DATA: Final[str] = "No SecretString or SecretBinary found in response for {secret_id}"

# Error messages
LOG_VAULT_BOTH_KV_FAILED: Final[str] = "Both KV v1 and v2 failed: {error}"
LOG_AWS_FETCH_FAILED: Final[str] = "Failed to fetch secret from AWS Secrets Manager: {error}"

# =============================================================================
# Installation Messages
# =============================================================================

INSTALL_VAULT: Final[str] = "pip install mlflow-secrets-auth[vault]"
INSTALL_AWS: Final[str] = "pip install mlflow-secrets-auth[aws]"
INSTALL_AZURE: Final[str] = "pip install mlflow-secrets-auth[azure]"
INSTALL_ALL: Final[str] = "pip install mlflow-secrets-auth[vault,aws,azure]"

# =============================================================================
# Help and Usage Messages
# =============================================================================

USAGE_SECRET_FORMATS: Final[str] = """
Supported secret formats:
  - {"token": "<opaque token>"}
  - {"username": "...", "password": "..."}
  - "username:password" → {"username": "...", "password": "..."}
  - "<token>" → {"token": "<token>"}
"""

USAGE_WILDCARD_HOSTS: Final[str] = """
Wildcard patterns for allowed hosts:
  - "*.corp.example.com" matches any subdomain of corp.example.com
  - "mlflow.*.com" matches mlflow with any middle component
  - "api-*" matches hostnames starting with "api-"
"""

# =============================================================================
# Time Format Messages
# =============================================================================

TIME_FORMAT_SECONDS: Final[str] = "{seconds}s"
TIME_FORMAT_MINUTES_SECONDS: Final[str] = "{minutes}m {seconds}s"
TIME_FORMAT_HOURS: Final[str] = "{hours}h"
TIME_FORMAT_HOURS_MINUTES: Final[str] = "{hours}h {minutes}m"

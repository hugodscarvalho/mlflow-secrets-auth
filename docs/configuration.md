# Configuration

Complete reference for configuring MLflow Secrets Auth, including environment variables, security settings, and provider-specific options.

## Overview

MLflow Secrets Auth is configured entirely through environment variables, making it suitable for containerized deployments and CI/CD pipelines. Configuration covers provider selection, authentication parameters, security settings, and performance tuning.

## Global Configuration

### Provider Selection

#### Primary Control

```bash
# Enable specific providers (comma-separated)
MLFLOW_SECRETS_AUTH_ENABLE="vault,aws-secrets-manager,azure-key-vault"

# Provider priority order (first available is used):
# 1. vault
# 2. aws-secrets-manager  
# 3. azure-key-vault
```

#### Per-Provider Control

```bash
# Individual provider toggles
MLFLOW_SECRETS_AUTH_ENABLE_VAULT=true
MLFLOW_SECRETS_AUTH_ENABLE_AWS_SECRETS_MANAGER=true
MLFLOW_SECRETS_AUTH_ENABLE_AZURE_KEY_VAULT=true
```

### Security Configuration

#### Host Allowlisting

Control which MLflow servers can receive authentication credentials:

```bash
# Exact hostnames
MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com,mlflow-staging.company.com"

# Wildcard patterns (shell-style globbing)
MLFLOW_SECRETS_ALLOWED_HOSTS="*.company.com,localhost,127.0.0.1"

# Mixed patterns
MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.prod.com,*.staging.com,localhost"
```

**Wildcard Examples**:
- `*.company.com` - Matches any subdomain of company.com
- `mlflow-*` - Matches hostnames starting with "mlflow-"
- `api.*.com` - Matches api with any middle component

**Security Note**: Always use allowlisting in production environments to prevent credential leakage to unauthorized hosts.

#### Authentication Headers

```bash
# Custom authentication header name (default: "Authorization")
MLFLOW_AUTH_HEADER_NAME="X-MLflow-Auth"

# Authentication modes supported:
# - bearer: Authorization: Bearer <token>
# - basic: Authorization: Basic <base64(username:password)>
```

### Logging Configuration

```bash
# Log level for secrets auth components
MLFLOW_SECRETS_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR

# Logging behavior:
# - Automatic credential redaction in all log output
# - Structured logging for integration with monitoring systems
# - Provider-specific debug information when enabled
```

## Provider-Specific Configuration

### HashiCorp Vault

#### Authentication

```bash
# Vault server address (required)
VAULT_ADDR="https://vault.company.com"

# Token authentication (preferred for simplicity)
VAULT_TOKEN="hvs.XXXXXXXXXXXXXXXX"

# AppRole authentication (preferred for automation)
VAULT_ROLE_ID="role-id-value"
VAULT_SECRET_ID="secret-id-value"
```

#### Secret Path Configuration

```bash
# Secret path in Vault (required)
MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"

# Path formats supported:
# - KV v2: "secret/mlflow/auth" (auto-detects and uses secret/data/mlflow/auth)
# - KV v2 explicit: "secret/data/mlflow/auth"
# - KV v1: "secret/mlflow/auth" (fallback behavior)
```

#### Vault-Specific Options

```bash
# Authentication mode
MLFLOW_VAULT_AUTH_MODE="bearer"  # bearer, basic

# Cache TTL in seconds
MLFLOW_VAULT_TTL_SEC=300  # 5 minutes (default)

# Vault client configuration (advanced)
VAULT_NAMESPACE="namespace"  # For Vault Enterprise
VAULT_SKIP_VERIFY="false"   # Skip TLS verification (not recommended)
```

### AWS Secrets Manager

#### AWS Authentication

```bash
# AWS region (required)
AWS_REGION="us-east-1"

# AWS credentials (one method required):
# 1. IAM User credentials
AWS_ACCESS_KEY_ID="AKIAXXXXXXXXXXXXXXXX"
AWS_SECRET_ACCESS_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 2. IAM Role (EC2/ECS/Lambda)
# Automatically detected via instance metadata

# 3. AWS Profile
AWS_PROFILE="mlflow-profile"

# 4. AssumeRole
AWS_ROLE_ARN="arn:aws:iam::123456789012:role/MLflowRole"
AWS_ROLE_SESSION_NAME="mlflow-session"
```

#### Secret Configuration

```bash
# Secret name or ARN (required)
MLFLOW_AWS_SECRET_NAME="mlflow/auth"
# OR
MLFLOW_AWS_SECRET_NAME="arn:aws:secretsmanager:us-east-1:123456789012:secret:mlflow/auth-AbCdEf"

# Version handling
MLFLOW_AWS_SECRET_VERSION="AWSCURRENT"  # AWSCURRENT, AWSPENDING, or specific version
```

#### AWS-Specific Options

```bash
# Authentication mode
MLFLOW_AWS_AUTH_MODE="bearer"  # bearer, basic

# Cache TTL in seconds
MLFLOW_AWS_TTL_SEC=300  # 5 minutes (default)

# Retry configuration
MLFLOW_AWS_MAX_RETRIES=3
MLFLOW_AWS_RETRY_MODE="adaptive"  # legacy, standard, adaptive
```

### Azure Key Vault

#### Azure Authentication

```bash
# Service Principal authentication
AZURE_TENANT_ID="tenant-id-uuid"
AZURE_CLIENT_ID="client-id-uuid"
AZURE_CLIENT_SECRET="client-secret-value"

# Or Certificate-based authentication
AZURE_CLIENT_CERTIFICATE_PATH="/path/to/certificate.pem"

# Or Managed Identity (Azure VMs/App Service)
AZURE_CLIENT_ID="managed-identity-client-id"  # Optional for user-assigned MI
```

#### Key Vault Configuration

```bash
# Key Vault URL (required)
MLFLOW_AZURE_KEY_VAULT_URL="https://your-vault.vault.azure.net/"

# Secret name (required)
MLFLOW_AZURE_SECRET_NAME="mlflow-auth"

# Secret version (optional)
MLFLOW_AZURE_SECRET_VERSION="latest"  # latest, or specific version ID
```

#### Azure-Specific Options

```bash
# Authentication mode
MLFLOW_AZURE_AUTH_MODE="bearer"  # bearer, basic

# Cache TTL in seconds
MLFLOW_AZURE_TTL_SEC=300  # 5 minutes (default)

# Azure cloud environment
AZURE_CLOUD_ENVIRONMENT="AzurePublicCloud"  # AzurePublicCloud, AzureUSGovernment, etc.
```

## Secret Format Requirements

### Bearer Token Authentication

Secrets should contain a `token` field:

```json
{
  "token": "your-bearer-token-value"
}
```

### Basic Authentication

Secrets should contain `username` and `password` fields:

```json
{
  "username": "mlflow-user",
  "password": "secure-password"
}
```

### Custom Authentication

For custom header formats, include the complete header value:

```json
{
  "token": "custom-auth-scheme token-value"
}
```

## Performance Configuration

### Caching

```bash
# Cache TTL per provider (seconds)
MLFLOW_VAULT_TTL_SEC=300
MLFLOW_AWS_TTL_SEC=300
MLFLOW_AZURE_TTL_SEC=300

# Cache behavior:
# - In-memory only (not persisted)
# - Automatic cache busting on 401/403 responses
# - Per-configuration caching (different configs = different cache entries)
```

### Retry Configuration

```bash
# Retry attempts for secret fetching
MLFLOW_SECRETS_MAX_RETRIES=3

# Retry behavior:
# - Exponential backoff with jitter
# - Automatic retry on transient failures
# - Different retry strategies per provider
```

## Environment-Specific Examples

### Development Environment

```bash
# Local development with Vault
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="dev-token"
export MLFLOW_VAULT_SECRET_PATH="secret/dev/mlflow"
export MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,127.0.0.1,*.local"
export MLFLOW_SECRETS_AUTH_ENABLE="vault"
export MLFLOW_SECRETS_LOG_LEVEL="DEBUG"
```

### Staging Environment

```bash
# AWS Secrets Manager for staging
export AWS_REGION="us-east-1"
export MLFLOW_AWS_SECRET_NAME="staging/mlflow/auth"
export MLFLOW_SECRETS_ALLOWED_HOSTS="*.staging.company.com"
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"
export MLFLOW_SECRETS_LOG_LEVEL="INFO"
export MLFLOW_AWS_TTL_SEC=600  # 10 minutes for staging
```

### Production Environment

```bash
# Azure Key Vault for production
export AZURE_TENANT_ID="${AZURE_TENANT_ID}"
export AZURE_CLIENT_ID="${AZURE_CLIENT_ID}"
export AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET}"
export MLFLOW_AZURE_KEY_VAULT_URL="https://prod-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-prod-auth"
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"
export MLFLOW_SECRETS_LOG_LEVEL="WARNING"
export MLFLOW_AZURE_TTL_SEC=900  # 15 minutes for production
```

### Multi-Provider Fallback

```bash
# Production with multiple providers for resilience
export MLFLOW_SECRETS_AUTH_ENABLE="vault,aws-secrets-manager,azure-key-vault"

# Vault (primary)
export VAULT_ADDR="https://vault.company.com"
export VAULT_TOKEN="${VAULT_TOKEN}"
export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"

# AWS (secondary)
export AWS_REGION="us-east-1"
export MLFLOW_AWS_SECRET_NAME="mlflow/auth"

# Azure (tertiary)
export MLFLOW_AZURE_KEY_VAULT_URL="https://backup-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-auth"

# Shared configuration
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
export MLFLOW_SECRETS_LOG_LEVEL="INFO"
```

## Configuration Validation

### CLI Validation

```bash
# Check current configuration
mlflow-secrets-auth info

# Test configuration against specific URL
mlflow-secrets-auth doctor --dry-run https://mlflow.company.com

# Debug configuration issues
MLFLOW_SECRETS_LOG_LEVEL=DEBUG mlflow-secrets-auth doctor
```

### Programmatic Validation

```python
from mlflow_secrets_auth.config import (
    is_provider_enabled,
    get_allowed_hosts,
    get_auth_header_name
)

# Check if providers are enabled
print(f"Vault enabled: {is_provider_enabled('vault')}")
print(f"AWS enabled: {is_provider_enabled('aws-secrets-manager')}")
print(f"Azure enabled: {is_provider_enabled('azure-key-vault')}")

# Check security configuration
print(f"Allowed hosts: {get_allowed_hosts()}")
print(f"Auth header: {get_auth_header_name()}")
```

## Security Best Practices

### Environment Variable Security

1. **Use Secret Management**: Store sensitive values in your platform's secret management system
2. **Limit Scope**: Use environment-specific configurations
3. **Rotate Regularly**: Implement automatic credential rotation
4. **Monitor Access**: Log and monitor configuration access

### Host Allowlisting

1. **Always Enable**: Use `MLFLOW_SECRETS_ALLOWED_HOSTS` in production
2. **Principle of Least Privilege**: Only allow necessary hosts
3. **Wildcard Caution**: Use wildcards carefully and specifically
4. **Regular Review**: Audit allowed hosts regularly

### Provider Security

1. **IAM Best Practices**: Use minimal required permissions
2. **Network Security**: Use private networks and VPNs when possible
3. **Audit Logging**: Enable audit logging on secret management systems
4. **Regular Updates**: Keep provider SDKs updated

## Troubleshooting Configuration

### Common Issues

1. **Provider Not Recognized**: Check `MLFLOW_SECRETS_AUTH_ENABLE` value
2. **Host Not Allowed**: Verify `MLFLOW_SECRETS_ALLOWED_HOSTS` patterns
3. **Secret Not Found**: Validate secret paths and names
4. **Authentication Failed**: Check provider credentials and permissions

### Debug Commands

```bash
# Enable verbose logging
export MLFLOW_SECRETS_LOG_LEVEL=DEBUG

# Test provider authentication
mlflow-secrets-auth doctor

# Check configuration summary
mlflow-secrets-auth info
```

## Next Steps

- **[CLI Reference](cli.md)** - Command-line tools for testing and diagnostics
- **[Provider Documentation](providers/)** - Provider-specific configuration details
- **[Security Guide](concepts/security.md)** - Security concepts and best practices
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

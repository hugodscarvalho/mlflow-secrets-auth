# Getting Started

This guide provides a step-by-step walkthrough for setting up MLflow Secrets Auth with your preferred secret management provider.

## Prerequisites

- Python 3.9 or higher
- MLflow 2.20.4 or higher
- Access to one of the supported secret managers:
  - HashiCorp Vault
  - AWS Secrets Manager
  - Azure Key Vault

## Step 1: Installation

Choose your installation method based on your secret management provider:

### Basic Installation

```bash
pip install mlflow-secrets-auth
```

### Provider-Specific Installation

```bash
# For HashiCorp Vault
pip install mlflow-secrets-auth[vault]

# For AWS Secrets Manager
pip install mlflow-secrets-auth[aws]

# For Azure Key Vault
pip install mlflow-secrets-auth[azure]

# For multiple providers
pip install mlflow-secrets-auth[vault,aws,azure]
```

## Step 2: Provider Setup

### Option A: HashiCorp Vault

1. **Configure Vault Access**
   ```bash
   export VAULT_ADDR="https://vault.company.com"
   export VAULT_TOKEN="hvs.XXXXXXXXXXXXXXXX"
   # OR use AppRole authentication
   export VAULT_ROLE_ID="role-id-value"
   export VAULT_SECRET_ID="secret-id-value"
   ```

2. **Set Secret Path**
   ```bash
   export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
   ```

3. **Store Secret in Vault**
   ```bash
   # For Bearer token authentication
   vault kv put secret/mlflow/auth token="your-mlflow-token"
   
   # For Basic authentication
   vault kv put secret/mlflow/auth username="user" password="pass"
   ```

### Option B: AWS Secrets Manager

1. **Configure AWS Credentials**
   ```bash
   export AWS_REGION="us-east-1"
   # AWS credentials via IAM role, profile, or environment variables
   ```

2. **Set Secret Name**
   ```bash
   export MLFLOW_AWS_SECRET_NAME="mlflow/auth"
   ```

3. **Create Secret in AWS**
   ```bash
   aws secretsmanager create-secret \
     --name "mlflow/auth" \
     --secret-string '{"token":"your-mlflow-token"}'
   ```

### Option C: Azure Key Vault

1. **Configure Azure Authentication**
   ```bash
   export AZURE_TENANT_ID="your-tenant-id"
   export AZURE_CLIENT_ID="your-client-id"
   export AZURE_CLIENT_SECRET="your-client-secret"
   ```

2. **Set Key Vault Details**
   ```bash
   export MLFLOW_AZURE_KEY_VAULT_URL="https://your-vault.vault.azure.net/"
   export MLFLOW_AZURE_SECRET_NAME="mlflow-auth"
   ```

3. **Store Secret in Azure Key Vault**
   ```bash
   az keyvault secret set \
     --vault-name "your-vault" \
     --name "mlflow-auth" \
     --value '{"token":"your-mlflow-token"}'
   ```

## Step 3: Enable the Plugin

Enable your chosen provider:

```bash
# Enable specific provider
export MLFLOW_SECRETS_AUTH_ENABLE="vault"
# OR
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"
# OR
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"

# Enable multiple providers (first available will be used)
export MLFLOW_SECRETS_AUTH_ENABLE="vault,aws-secrets-manager,azure-key-vault"
```

## Step 4: Configure Security (Recommended)

Set up host allowlisting to restrict which MLflow servers can receive credentials:

```bash
# Allow specific hosts
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com,mlflow-staging.company.com"

# Allow wildcard patterns
export MLFLOW_SECRETS_ALLOWED_HOSTS="*.company.com,localhost"
```

## Step 5: Test the Setup

### Verify Configuration

```bash
# Check plugin status and configuration
mlflow-secrets-auth info

# Run diagnostics
mlflow-secrets-auth doctor

# Test against your MLflow server
mlflow-secrets-auth doctor --dry-run https://mlflow.company.com
```

### Test with MLflow

```python
import mlflow

# Set your MLflow tracking URI
mlflow.set_tracking_uri("https://mlflow.company.com")

# Authentication happens automatically
mlflow.start_run()
mlflow.log_param("test", "setup")
mlflow.log_metric("status", 1.0)
mlflow.end_run()

print("Setup successful!")
```

## Step 6: Environment Variables Summary

Create a `.env` file or set these environment variables in your deployment:

```bash
# Provider Selection
MLFLOW_SECRETS_AUTH_ENABLE=vault

# Vault Configuration (if using Vault)
VAULT_ADDR=https://vault.company.com
VAULT_TOKEN=hvs.XXXXXXXXXXXXXXXX
MLFLOW_VAULT_SECRET_PATH=secret/mlflow/auth

# Security Configuration
MLFLOW_SECRETS_ALLOWED_HOSTS=*.company.com,localhost

# Optional: Logging and Performance
MLFLOW_SECRETS_LOG_LEVEL=INFO
MLFLOW_VAULT_TTL_SEC=300
```

## Common Use Cases

### Development Environment

```bash
# Local development with Vault
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="dev-token"
export MLFLOW_VAULT_SECRET_PATH="secret/dev/mlflow"
export MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,127.0.0.1"
export MLFLOW_SECRETS_AUTH_ENABLE="vault"
```

### Production Environment

```bash
# Production with AWS Secrets Manager
export AWS_REGION="us-east-1"
export MLFLOW_AWS_SECRET_NAME="production/mlflow/auth"
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"
export MLFLOW_SECRETS_LOG_LEVEL="WARNING"
```

### CI/CD Pipeline

```bash
# Azure Key Vault for CI/CD
export AZURE_TENANT_ID="${AZURE_TENANT_ID}"
export AZURE_CLIENT_ID="${AZURE_CLIENT_ID}"
export AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET}"
export MLFLOW_AZURE_KEY_VAULT_URL="https://ci-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-ci-auth"
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow-ci.company.com"
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"
```

## Next Steps

- **[Configuration Reference](configuration.md)** - Complete environment variable reference
- **[Provider Documentation](providers/)** - Provider-specific configuration details
- **[CLI Tools](cli.md)** - Command-line utilities and diagnostics
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

## Troubleshooting Quick Start

If you encounter issues during setup:

1. **Check Plugin Status**
   ```bash
   mlflow-secrets-auth info
   ```

2. **Run Diagnostics**
   ```bash
   mlflow-secrets-auth doctor --dry-run https://your-mlflow-server.com
   ```

3. **Enable Debug Logging**
   ```bash
   export MLFLOW_SECRETS_LOG_LEVEL=DEBUG
   ```

4. **Verify Provider Dependencies**
   ```bash
   python -c "import hvac; print('Vault OK')"  # For Vault
   python -c "import boto3; print('AWS OK')"   # For AWS
   python -c "import azure.identity; print('Azure OK')"  # For Azure
   ```

For detailed troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).

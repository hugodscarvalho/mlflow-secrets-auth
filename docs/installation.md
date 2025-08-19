# Installation

This guide covers installation of MLflow Secrets Auth with provider-specific dependencies and configuration requirements.

## System Requirements

- **Python**: 3.9 or higher
- **MLflow**: 2.20.4 or higher (mlflow-skinny supported)
- **Operating System**: Linux, macOS, Windows
- **Secret Manager Access**: Valid credentials for at least one supported provider

## Installation Methods

### Basic Installation

Install the core plugin without provider dependencies:

```bash
pip install mlflow-secrets-auth
```

This installation includes the plugin framework but requires manual installation of provider SDKs.

### Provider-Specific Installation

Install with provider-specific dependencies using extras:

#### HashiCorp Vault

```bash
pip install mlflow-secrets-auth[vault]
```

**Includes**: `hvac>=2.3.0`

#### AWS Secrets Manager

```bash
pip install mlflow-secrets-auth[aws]
```

**Includes**: `boto3>=1.40.11`

#### Azure Key Vault

```bash
pip install mlflow-secrets-auth[azure]
```

**Includes**: `azure-identity>=1.24.0`, `azure-keyvault-secrets>=4.10.0`

### Multiple Providers

Install support for multiple providers:

```bash
# All providers
pip install mlflow-secrets-auth[vault,aws,azure]

# Specific combinations
pip install mlflow-secrets-auth[vault,aws]
pip install mlflow-secrets-auth[aws,azure]
```

## Advanced Installation Options

### Development Installation

For development or contributing to the project:

```bash
git clone https://github.com/hugodscarvalho/mlflow-secrets-auth.git
cd mlflow-secrets-auth
pip install -e .[vault,aws,azure]
```

### Poetry Installation

If using Poetry for dependency management:

```bash
# Add to pyproject.toml
poetry add mlflow-secrets-auth[vault,aws,azure]

# Or install specific providers
poetry add mlflow-secrets-auth[vault]
```

### Docker Installation

For containerized environments:

```dockerfile
# Dockerfile example
FROM python:3.11-slim

# Install with all providers
RUN pip install mlflow-secrets-auth[vault,aws,azure]

# Your application code
COPY . /app
WORKDIR /app
```

## Verification

### Check Installation

Verify the plugin is installed correctly:

```bash
# Check package installation
pip show mlflow-secrets-auth

# Verify plugin registration
python -c "import mlflow_secrets_auth; print(mlflow_secrets_auth.__version__)"

# Check CLI availability
mlflow-secrets-auth info
```

### Verify Provider Dependencies

Check that provider dependencies are available:

```bash
# Vault support
python -c "import hvac; print('✓ Vault support available')"

# AWS support
python -c "import boto3; print('✓ AWS support available')"

# Azure support
python -c "import azure.identity, azure.keyvault.secrets; print('✓ Azure support available')"
```

## Provider-Specific Setup

### HashiCorp Vault

#### Prerequisites

- Vault server accessible from your environment
- Valid authentication method (token or AppRole)
- Appropriate policies for secret access

#### Required Permissions

Vault policy example for KV v2:

```hcl
# Policy: mlflow-secrets-auth
path "secret/data/mlflow/*" {
  capabilities = ["read"]
}

path "secret/metadata/mlflow/*" {
  capabilities = ["read"]
}
```

#### Minimal Configuration

```bash
export VAULT_ADDR="https://vault.company.com"
export VAULT_TOKEN="hvs.XXXXXXXXXXXXXXXX"
export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="vault"
```

### AWS Secrets Manager

#### Prerequisites

- AWS account with Secrets Manager access
- Valid AWS credentials (IAM user, role, or instance profile)
- Appropriate IAM permissions

#### Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:region:account:secret:mlflow/*"
    }
  ]
}
```

#### Minimal Configuration

```bash
export AWS_REGION="us-east-1"
export MLFLOW_AWS_SECRET_NAME="mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"
```

### Azure Key Vault

#### Prerequisites

- Azure subscription with Key Vault access
- Service principal or managed identity
- Appropriate access policies

#### Required Access Policies

Key Vault access policy for secrets:

```bash
az keyvault set-policy \
  --name "your-vault" \
  --spn "service-principal-id" \
  --secret-permissions get
```

#### Minimal Configuration

```bash
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export MLFLOW_AZURE_KEY_VAULT_URL="https://your-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-auth"
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"
```

## Optional Dependencies

### MLflow Server

For local MLflow server development:

```bash
pip install mlflow-secrets-auth[vault] mlflow
```

### Testing Dependencies

For running tests:

```bash
pip install mlflow-secrets-auth[vault,aws,azure] pytest pytest-cov
```

## Environment-Specific Considerations

### Production Environments

- Use specific version pins for reproducible deployments
- Consider security scanning of dependencies
- Implement proper secret rotation strategies
- Use managed identities when available

### CI/CD Pipelines

- Cache pip dependencies for faster builds
- Use environment-specific extras
- Implement proper credential management
- Test with minimal permission sets

### Kubernetes Deployments

- Use init containers for dependency installation
- Leverage service accounts for cloud provider authentication
- Implement proper resource limits
- Consider using distroless base images

## Troubleshooting Installation

### Common Issues

#### Missing Provider Dependencies

**Error**: `ImportError: No module named 'hvac'`

**Solution**: Install with provider extras:
```bash
pip install mlflow-secrets-auth[vault]
```

#### Version Conflicts

**Error**: Package version conflicts

**Solution**: Use virtual environments:
```bash
python -m venv mlflow-env
source mlflow-env/bin/activate  # Linux/macOS
# mlflow-env\Scripts\activate  # Windows
pip install mlflow-secrets-auth[vault,aws,azure]
```

#### Plugin Not Recognized

**Error**: MLflow doesn't recognize the auth provider

**Solution**: Verify entry point registration:
```bash
python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('mlflow.request_auth_provider'):
    print(f'{ep.name}: {ep.module_name}')
"
```

### Debug Installation

Enable verbose logging during installation:

```bash
pip install -v mlflow-secrets-auth[vault,aws,azure]
```

Check installed packages and versions:

```bash
pip list | grep -E "(mlflow|vault|boto3|azure)"
```

## Next Steps

After successful installation:

1. **[Configuration](configuration.md)** - Set up environment variables and security settings
2. **[Getting Started](getting-started.md)** - Quick start guide with examples
3. **[Provider Documentation](providers/)** - Provider-specific configuration
4. **[CLI Tools](cli.md)** - Command-line utilities for testing and diagnostics

## Uninstallation

To remove the plugin and its dependencies:

```bash
# Remove the main package
pip uninstall mlflow-secrets-auth

# Remove provider dependencies if not needed
pip uninstall hvac boto3 azure-identity azure-keyvault-secrets
```

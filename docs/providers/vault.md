# HashiCorp Vault Provider

The Vault provider enables MLflow Secrets Auth to retrieve credentials from HashiCorp Vault using either token-based or AppRole authentication methods. It supports both KV v1 and KV v2 secret engines with automatic detection and fallback.

## Overview

HashiCorp Vault is a secrets management solution that provides secure storage, dynamic secrets, and data encryption. The MLflow Secrets Auth Vault provider integrates seamlessly with Vault's authentication and authorization model.

### Features

- **Multiple Authentication Methods**: Token and AppRole support
- **KV Engine Support**: Automatic detection of KV v1 and KV v2 engines
- **Graceful Fallback**: Falls back from KV v2 to KV v1 automatically
- **Path Flexibility**: Supports various secret path formats
- **Enterprise Features**: Namespace support for Vault Enterprise
- **Connection Reuse**: Efficient client connection management

### Requirements

- **Vault Server**: HashiCorp Vault 1.0+ (KV v2 requires 1.0+)
- **Network Access**: HTTPS connectivity to Vault server
- **Authentication**: Valid Vault token or AppRole credentials
- **Permissions**: Read access to the specified secret path
- **Python Package**: `hvac>=2.3.0` (installed with `pip install mlflow-secrets-auth[vault]`)

## Installation

### Basic Installation

```bash
pip install mlflow-secrets-auth[vault]
```

### Verify Installation

```bash
python -c "import hvac; print('✓ Vault support available')"
```

## Authentication Methods

### Token Authentication

Token authentication is the simplest method for getting started with Vault.

#### Configuration

```bash
export VAULT_ADDR="https://vault.company.com"
export VAULT_TOKEN="hvs.XXXXXXXXXXXXXXXX"
export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="vault"
```

#### Token Requirements

- **Valid Token**: Must be unexpired and have necessary permissions
- **Read Permissions**: Access to the secret path
- **Policy Assignment**: Token must be associated with appropriate policies

#### Example Vault Policy

```hcl
# Policy: mlflow-secrets-auth
path "secret/data/mlflow/*" {
  capabilities = ["read"]
}

path "secret/metadata/mlflow/*" {
  capabilities = ["read"]
}
```

### AppRole Authentication

AppRole authentication is recommended for automated systems and production deployments.

#### Configuration

```bash
export VAULT_ADDR="https://vault.company.com"
export VAULT_ROLE_ID="role-id-value"
export VAULT_SECRET_ID="secret-id-value"
export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="vault"
```

#### AppRole Setup

1. **Create AppRole**:
   ```bash
   vault auth enable approle
   
   vault write auth/approle/role/mlflow-secrets-auth \
     token_policies="mlflow-secrets-auth" \
     token_ttl=1h \
     token_max_ttl=4h
   ```

2. **Get Role ID**:
   ```bash
   vault read auth/approle/role/mlflow-secrets-auth/role-id
   ```

3. **Generate Secret ID**:
   ```bash
   vault write -f auth/approle/role/mlflow-secrets-auth/secret-id
   ```

#### AppRole Best Practices

- **Separate Roles**: Use different AppRoles per environment
- **TTL Management**: Configure appropriate token TTLs
- **Secret ID Rotation**: Regularly rotate Secret IDs
- **Response Wrapping**: Use response wrapping for Secret ID distribution

## Secret Path Configuration

### KV v2 Paths (Recommended)

KV v2 is the default and recommended secret engine for new Vault installations.

#### Standard KV v2 Path

```bash
# Secret stored at: secret/data/mlflow/auth
export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
```

#### Explicit KV v2 Path

```bash
# Explicit KV v2 path
export MLFLOW_VAULT_SECRET_PATH="secret/data/mlflow/auth"
```

#### Custom Mount Path

```bash
# Custom mount point
export MLFLOW_VAULT_SECRET_PATH="kv-v2/mlflow/auth"
```

### KV v1 Paths (Legacy)

KV v1 is supported for backward compatibility with older Vault installations.

#### KV v1 Configuration

```bash
# KV v1 path (legacy)
export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
```

### Path Resolution Logic

The provider automatically detects and handles different path formats:

1. **Try KV v2**: Attempt to read using KV v2 API
2. **Fallback to KV v1**: If KV v2 fails, try KV v1 API
3. **Path Normalization**: Automatically adjust paths for each API version

```python
# Internal path resolution
if secret_path.startswith("secret/data/"):
    # Explicit KV v2 path
    kv2_path = secret_path
else:
    # Convert to KV v2 format
    kv2_path = secret_path.replace("secret/", "secret/data/", 1)

# Try KV v2 first
try:
    response = client.secrets.kv.v2.read_secret_version(path=kv2_relative_path)
except:
    # Fallback to KV v1
    response = client.secrets.kv.v1.read_secret(path=kv1_relative_path)
```

## Secret Format

### Bearer Token Authentication

Store the authentication token in a `token` field:

```bash
# Store secret in Vault
vault kv put secret/mlflow/auth token="your-mlflow-bearer-token"
```

**JSON Structure**:
```json
{
  "token": "your-mlflow-bearer-token"
}
```

### Basic Authentication

Store username and password for Basic authentication:

```bash
# Store secret in Vault
vault kv put secret/mlflow/auth \
  username="mlflow-user" \
  password="secure-password"
```

**JSON Structure**:
```json
{
  "username": "mlflow-user", 
  "password": "secure-password"
}
```

### Custom Fields

Include additional metadata if needed:

```bash
# Store secret with metadata
vault kv put secret/mlflow/auth \
  token="bearer-token" \
  description="MLflow production auth" \
  created_by="admin" \
  environment="production"
```

**JSON Structure**:
```json
{
  "token": "bearer-token",
  "description": "MLflow production auth",
  "created_by": "admin",
  "environment": "production"
}
```

## Configuration Reference

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VAULT_ADDR` | Vault server URL | `https://vault.company.com` |
| `MLFLOW_VAULT_SECRET_PATH` | Path to secret in Vault | `secret/mlflow/auth` |

### Authentication Variables

#### Token Authentication

| Variable | Description | Example |
|----------|-------------|---------|
| `VAULT_TOKEN` | Vault authentication token | `hvs.XXXXXXXXXXXXXXXX` |

#### AppRole Authentication  

| Variable | Description | Example |
|----------|-------------|---------|
| `VAULT_ROLE_ID` | AppRole role identifier | `role-id-value` |
| `VAULT_SECRET_ID` | AppRole secret identifier | `secret-id-value` |

### Optional Configuration

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `MLFLOW_VAULT_AUTH_MODE` | `bearer` | Authentication mode | `bearer`, `basic` |
| `MLFLOW_VAULT_TTL_SEC` | `300` | Cache TTL in seconds | `600` |
| `VAULT_NAMESPACE` | None | Vault namespace (Enterprise) | `production` |
| `VAULT_SKIP_VERIFY` | `false` | Skip TLS verification | `true` (not recommended) |

## Examples

### Development Environment

```bash
#!/bin/bash
# Development setup with Vault

# Vault configuration
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="dev-only-token"

# MLflow Secrets Auth configuration  
export MLFLOW_VAULT_SECRET_PATH="secret/dev/mlflow"
export MLFLOW_VAULT_AUTH_MODE="bearer"
export MLFLOW_VAULT_TTL_SEC="60"  # Short TTL for development
export MLFLOW_SECRETS_AUTH_ENABLE="vault"

# Security configuration (permissive for development)
export MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,127.0.0.1,*.local"
export MLFLOW_SECRETS_LOG_LEVEL="DEBUG"

# Store development secret
vault kv put secret/dev/mlflow token="dev-token-123"

# Test configuration
mlflow-secrets-auth doctor --dry-run http://localhost:5000
```

### Production Environment

```bash
#!/bin/bash  
# Production setup with AppRole

# Vault configuration
export VAULT_ADDR="https://vault.company.com"
export VAULT_ROLE_ID="${VAULT_ROLE_ID}"  # From secure storage
export VAULT_SECRET_ID="${VAULT_SECRET_ID}"  # From secure storage

# MLflow Secrets Auth configuration
export MLFLOW_VAULT_SECRET_PATH="secret/prod/mlflow/auth"
export MLFLOW_VAULT_AUTH_MODE="bearer"
export MLFLOW_VAULT_TTL_SEC="900"  # 15 minutes for production
export MLFLOW_SECRETS_AUTH_ENABLE="vault"

# Security configuration
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
export MLFLOW_SECRETS_LOG_LEVEL="INFO"

# Validate configuration
mlflow-secrets-auth doctor
```

### Multi-Environment Setup

```bash
#!/bin/bash
# Environment-specific configuration

ENVIRONMENT=${ENVIRONMENT:-development}

case $ENVIRONMENT in
  development)
    export VAULT_ADDR="http://localhost:8200"
    export VAULT_TOKEN="dev-token"
    export MLFLOW_VAULT_SECRET_PATH="secret/dev/mlflow"
    export MLFLOW_VAULT_TTL_SEC="60"
    export MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,*.local"
    ;;
    
  staging)
    export VAULT_ADDR="https://vault-staging.company.com"
    export VAULT_ROLE_ID="${STAGING_VAULT_ROLE_ID}"
    export VAULT_SECRET_ID="${STAGING_VAULT_SECRET_ID}"
    export MLFLOW_VAULT_SECRET_PATH="secret/staging/mlflow/auth"
    export MLFLOW_VAULT_TTL_SEC="300"
    export MLFLOW_SECRETS_ALLOWED_HOSTS="*.staging.company.com"
    ;;
    
  production)
    export VAULT_ADDR="https://vault.company.com"
    export VAULT_ROLE_ID="${PROD_VAULT_ROLE_ID}"
    export VAULT_SECRET_ID="${PROD_VAULT_SECRET_ID}"
    export MLFLOW_VAULT_SECRET_PATH="secret/prod/mlflow/auth"
    export MLFLOW_VAULT_TTL_SEC="900"
    export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
    ;;
esac

export MLFLOW_SECRETS_AUTH_ENABLE="vault"
mlflow-secrets-auth doctor
```

## Vault Enterprise Features

### Namespace Support

Vault Enterprise supports namespaces for multi-tenancy:

```bash
# Configure namespace
export VAULT_NAMESPACE="production"
export VAULT_ADDR="https://vault.company.com"
export VAULT_TOKEN="hvs.XXXXXXXXXXXXXXXX"
export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
```

### Performance Standby

When using Vault Enterprise with Performance Standby:

```bash
# Primary cluster
export VAULT_ADDR="https://vault-primary.company.com"

# Performance standby (read-only operations)
export VAULT_ADDR="https://vault-standby.company.com"
```

## Troubleshooting

### Common Issues

#### Authentication Failures

**Problem**: `Vault authentication failed`

**Solutions**:
1. **Check Token Validity**:
   ```bash
   vault token lookup $VAULT_TOKEN
   ```

2. **Verify AppRole Credentials**:
   ```bash
   vault write auth/approle/login \
     role_id="$VAULT_ROLE_ID" \
     secret_id="$VAULT_SECRET_ID"
   ```

3. **Check Token Permissions**:
   ```bash
   vault token capabilities $VAULT_TOKEN secret/data/mlflow/auth
   ```

#### Path Not Found

**Problem**: `Secret not found at path`

**Solutions**:
1. **Verify Secret Exists**:
   ```bash
   vault kv get secret/mlflow/auth
   ```

2. **Check Path Format**:
   ```bash
   # KV v2
   vault kv get -mount=secret mlflow/auth
   
   # KV v1
   vault read secret/mlflow/auth
   ```

3. **List Available Paths**:
   ```bash
   vault kv list secret/
   ```

#### Network Connectivity

**Problem**: `Connection timeout to vault.company.com`

**Solutions**:
1. **Test Network Connectivity**:
   ```bash
   curl -k https://vault.company.com/v1/sys/health
   ```

2. **Check DNS Resolution**:
   ```bash
   nslookup vault.company.com
   ```

3. **Verify TLS Configuration**:
   ```bash
   openssl s_client -connect vault.company.com:443
   ```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export MLFLOW_SECRETS_LOG_LEVEL="DEBUG"
mlflow-secrets-auth doctor
```

**Debug Output Includes**:
- Vault client configuration
- Authentication method selection
- KV engine detection attempts
- Path resolution logic
- Secret parsing details

### CLI Diagnostics

Use the CLI for comprehensive diagnostics:

```bash
# Basic configuration check
mlflow-secrets-auth info

# Full diagnostic with Vault connectivity
mlflow-secrets-auth doctor

# Test against MLflow server
mlflow-secrets-auth doctor --dry-run https://mlflow.company.com
```

## Security Considerations

### Token Security

1. **Token Rotation**: Regularly rotate Vault tokens
2. **TTL Management**: Use appropriate token TTLs
3. **Least Privilege**: Grant minimal required permissions
4. **Secure Storage**: Store tokens securely (environment variables, secret managers)

### Network Security

1. **TLS Encryption**: Always use HTTPS for Vault communication
2. **Certificate Validation**: Avoid `VAULT_SKIP_VERIFY=true` in production
3. **Network Segmentation**: Restrict network access to Vault
4. **Firewall Rules**: Implement appropriate firewall restrictions

### Audit and Monitoring

1. **Enable Audit Logging**:
   ```bash
   vault audit enable file file_path=/vault/logs/audit.log
   ```

2. **Monitor Access Patterns**: Review Vault audit logs regularly
3. **Alert on Failures**: Set up alerts for authentication failures
4. **Track Secret Access**: Monitor secret read operations

## Performance Optimization

### Connection Reuse

The provider automatically reuses Vault client connections:

```python
# Connection pooling is handled automatically
# Clients are cached and reused across requests
```

### Caching Strategy

Configure appropriate TTL for your use case:

```bash
# High-frequency access: longer TTL
MLFLOW_VAULT_TTL_SEC=1800  # 30 minutes

# Security-sensitive: shorter TTL  
MLFLOW_VAULT_TTL_SEC=300   # 5 minutes

# Development: very short TTL
MLFLOW_VAULT_TTL_SEC=60    # 1 minute
```

### Vault Performance

1. **Use Vault Performance Standby**: For read-heavy workloads
2. **Optimize Vault Policies**: Use specific paths instead of wildcards
3. **Monitor Vault Metrics**: Track response times and error rates
4. **Scale Vault Cluster**: Add nodes for high availability and performance

## Migration and Upgrades

### KV v1 to KV v2 Migration

When migrating from KV v1 to KV v2:

1. **Enable KV v2**:
   ```bash
   vault secrets enable -path=secret kv-v2
   ```

2. **Migrate Secrets**:
   ```bash
   # Read from KV v1
   vault read secret/mlflow/auth
   
   # Write to KV v2
   vault kv put secret/mlflow/auth token="value"
   ```

3. **Update Configuration**: No changes needed - provider auto-detects

### Vault Version Compatibility

| Vault Version | KV v1 | KV v2 | Notes |
|---------------|-------|-------|-------|
| 0.10+ | ✅ | ❌ | KV v1 only |
| 1.0+ | ✅ | ✅ | Both supported |
| 1.1+ | ✅ | ✅ | Recommended |

## Integration Examples

### Docker Deployment

```dockerfile
FROM python:3.11-slim

# Install MLflow Secrets Auth with Vault support
RUN pip install mlflow-secrets-auth[vault]

# Copy application
COPY . /app
WORKDIR /app

# Environment variables will be provided at runtime
ENV VAULT_ADDR=""
ENV VAULT_TOKEN=""
ENV MLFLOW_VAULT_SECRET_PATH=""
ENV MLFLOW_SECRETS_AUTH_ENABLE="vault"

CMD ["python", "app.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow-app
spec:
  template:
    spec:
      containers:
      - name: mlflow-app
        image: mlflow-app:latest
        env:
        - name: VAULT_ADDR
          value: "https://vault.company.com"
        - name: VAULT_ROLE_ID
          valueFrom:
            secretKeyRef:
              name: vault-auth
              key: role-id
        - name: VAULT_SECRET_ID
          valueFrom:
            secretKeyRef:
              name: vault-auth
              key: secret-id
        - name: MLFLOW_VAULT_SECRET_PATH
          value: "secret/mlflow/auth"
        - name: MLFLOW_SECRETS_AUTH_ENABLE
          value: "vault"
```

### CI/CD Pipeline

```yaml
# GitHub Actions example
name: MLflow Pipeline
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Vault Auth
      env:
        VAULT_ADDR: ${{ secrets.VAULT_ADDR }}
        VAULT_ROLE_ID: ${{ secrets.VAULT_ROLE_ID }}
        VAULT_SECRET_ID: ${{ secrets.VAULT_SECRET_ID }}
        MLFLOW_VAULT_SECRET_PATH: "secret/ci/mlflow/auth"
        MLFLOW_SECRETS_AUTH_ENABLE: "vault"
      run: |
        pip install mlflow-secrets-auth[vault]
        mlflow-secrets-auth doctor
        python test_mlflow_integration.py
```

## Next Steps

- **[AWS Secrets Manager Provider](aws.md)** - AWS-specific configuration
- **[Azure Key Vault Provider](azure.md)** - Azure-specific configuration  
- **[Configuration Reference](../configuration.md)** - Complete environment variable reference
- **[Troubleshooting Guide](../troubleshooting.md)** - General troubleshooting information

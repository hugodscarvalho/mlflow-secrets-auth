# FAQ

Frequently asked questions about MLflow Secrets Auth, covering common use cases, configuration scenarios, and implementation details.

## General Questions

### What is MLflow Secrets Auth?

MLflow Secrets Auth is a plugin for MLflow that automatically injects authentication headers from secret management systems (Vault, AWS Secrets Manager, Azure Key Vault) into tracking requests. It provides secure, transparent authentication without requiring code changes in MLflow applications.

### Which secret managers are supported?

Currently supported providers:
- **HashiCorp Vault** - KV v1 and KV v2 engines
- **AWS Secrets Manager** - SecretString and SecretBinary support
- **Azure Key Vault** - Native Azure AD integration

### Does this require changes to my MLflow code?

No. The plugin integrates transparently with MLflow's authentication system. Your existing MLflow code continues to work unchanged:

```python
import mlflow

# No changes needed - authentication happens automatically
mlflow.set_tracking_uri("https://mlflow.company.com")
mlflow.start_run()
mlflow.log_metric("accuracy", 0.95)
```

### How does the plugin select which provider to use?

The plugin uses a priority-based selection:
1. **HashiCorp Vault** (first priority)
2. **AWS Secrets Manager** (second priority)  
3. **Azure Key Vault** (third priority)

The first enabled and properly configured provider is used. Enable providers using:
```bash
export MLFLOW_SECRETS_AUTH_ENABLE="vault,aws-secrets-manager,azure-key-vault"
```

## Authentication Modes

### What authentication modes are supported?

Two authentication modes are supported:

**Bearer Token** (default):
```
Authorization: Bearer <token>
```

**Basic Authentication**:
```
Authorization: Basic <base64(username:password)>
```

Configure the mode per provider:
```bash
export MLFLOW_VAULT_AUTH_MODE="bearer"      # or "basic"
export MLFLOW_AWS_AUTH_MODE="bearer"        # or "basic"  
export MLFLOW_AZURE_AUTH_MODE="bearer"      # or "basic"
```

### Can I use custom headers instead of "Authorization"?

Yes, configure a custom header name:
```bash
export MLFLOW_AUTH_HEADER_NAME="X-MLflow-Auth"
```

This changes the header from:
```
Authorization: Bearer <token>
```
to:
```
X-MLflow-Auth: Bearer <token>
```

### How do I handle token rotation?

The plugin supports automatic token rotation through several mechanisms:

1. **Cache TTL**: Configure short TTL for frequent rotation
   ```bash
   export MLFLOW_VAULT_TTL_SEC=300  # 5 minutes
   ```

2. **Automatic Cache Busting**: Authentication failures (401/403) automatically clear cache

3. **Version Support**: AWS and Azure support specific secret versions
   ```bash
   export MLFLOW_AWS_SECRET_VERSION="AWSCURRENT"
   export MLFLOW_AZURE_SECRET_VERSION="latest"
   ```

## Host Allowlisting

### What is host allowlisting and why should I use it?

Host allowlisting prevents credentials from being sent to unauthorized servers. It's a critical security feature that ensures secrets only reach intended MLflow servers.

**Without allowlisting**: Credentials could be sent to any server
**With allowlisting**: Credentials only sent to approved hosts

```bash
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com,*.staging.company.com"
```

### How do wildcard patterns work?

The plugin uses shell-style globbing patterns:

- `*.company.com` - Matches any subdomain of company.com
- `mlflow-*` - Matches hostnames starting with "mlflow-"
- `api.*.com` - Matches api with any middle component

Examples:
```bash
# Specific hosts
MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.prod.com,mlflow.staging.com"

# Subdomain wildcards
MLFLOW_SECRETS_ALLOWED_HOSTS="*.company.com"

# Multiple patterns
MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.prod.com,*.staging.com,localhost"
```

### What happens if I don't configure host allowlisting?

If `MLFLOW_SECRETS_ALLOWED_HOSTS` is not set, the plugin allows all hosts by default. This is convenient for development but **not recommended for production**.

**Development** (permissive):
```bash
# No restrictions - allows all hosts
unset MLFLOW_SECRETS_ALLOWED_HOSTS
```

**Production** (secure):
```bash
# Restrict to specific hosts
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
```

### Can I use localhost for development?

Yes, include localhost and common development patterns:
```bash
export MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,127.0.0.1,*.local,mlflow.company.com"
```

## Binary Secrets

### Does the plugin support binary secrets?

Yes, particularly with AWS Secrets Manager:

**AWS Secrets Manager**:
- **SecretString**: Standard JSON secrets (preferred)
- **SecretBinary**: Binary data automatically base64 encoded/decoded

**Vault**: Supports binary data as base64-encoded strings in JSON

**Azure Key Vault**: Supports binary data as base64-encoded strings

### How are binary secrets handled?

Binary secrets are automatically converted to base64 strings for transport and parsed back to the appropriate format:

```python
# Internal handling (automatic)
import base64

# Binary secret from AWS
binary_data = secret_response['SecretBinary']
token = base64.b64encode(binary_data).decode('utf-8')

# Use in authentication header
auth_header = f"Bearer {token}"
```

### What formats work for binary tokens?

Common binary token formats that work:

1. **JWT tokens** (binary-encoded)
2. **Custom binary tokens**
3. **Encrypted token data**
4. **Certificate-based tokens**

Store as binary in the secret manager, and the plugin handles encoding automatically.

## Caching and Performance

### How does caching work?

The plugin implements in-memory caching with configurable TTL:

1. **First Request**: Fetch secret from provider, cache result
2. **Subsequent Requests**: Return cached secret if not expired
3. **Cache Expiry**: Re-fetch secret after TTL expires
4. **Auth Failures**: Automatically clear cache on 401/403 responses

### How do I configure cache TTL?

Set TTL per provider (in seconds):
```bash
export MLFLOW_VAULT_TTL_SEC=300      # 5 minutes
export MLFLOW_AWS_TTL_SEC=600        # 10 minutes
export MLFLOW_AZURE_TTL_SEC=900      # 15 minutes
```

**Considerations**:
- **Short TTL**: Better security, more API calls
- **Long TTL**: Better performance, less responsive to changes
- **Production**: 15-30 minutes typical
- **Development**: 1-5 minutes for rapid iteration

### What happens when secrets change?

When secrets are updated in the secret manager:

1. **Cached Entries**: Continue using old secret until TTL expires
2. **Authentication Failures**: Automatically trigger cache refresh
3. **Manual Refresh**: Restart application to clear cache immediately

**Future Enhancement**: CLI command to manually clear cache:
```bash
# Future feature
mlflow-secrets-auth cache clear
```

### How can I optimize performance?

1. **Appropriate TTL**: Balance security and performance
   ```bash
   export MLFLOW_VAULT_TTL_SEC=1800  # 30 minutes for high-frequency access
   ```

2. **Regional Proximity**: Use secret managers in the same region
3. **Connection Reuse**: Plugin automatically reuses connections
4. **Monitor Cache Hit Rate**: Check with `mlflow-secrets-auth info`

## Security

### Is it safe to use in production?

Yes, the plugin is designed with production security in mind:

1. **Host Allowlisting**: Prevents credential leakage
2. **Credential Redaction**: Automatic masking in logs
3. **In-Memory Only**: No disk persistence of secrets
4. **TLS Enforcement**: All communications use HTTPS
5. **Principle of Least Privilege**: Minimal required permissions

### How are secrets protected in logs?

All sensitive data is automatically redacted:

**Before Redaction**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Secret: {"token": "abc123def456", "password": "secret123"}
```

**After Redaction**:
```
Authorization: Bearer eyJh********cCI6
Secret: {"token": "abc1********def4", "password": "secr********123"}
```

### What permissions are needed?

**Vault**:
```hcl
path "secret/data/mlflow/*" {
  capabilities = ["read"]
}
```

**AWS**:
```json
{
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": "arn:aws:secretsmanager:region:account:secret:mlflow/*"
}
```

**Azure**:
```bash
# Key Vault Secrets User role
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee "$AZURE_CLIENT_ID"
```

### How do I handle credential rotation?

1. **Automatic Detection**: Plugin detects authentication failures and refreshes cache
2. **Short TTL**: Use shorter cache TTL for more frequent rotation
3. **Staged Rotation**: Update secrets during low-traffic periods
4. **Monitoring**: Monitor authentication failure rates

## Deployment

### How do I deploy in Docker?

```dockerfile
FROM python:3.11-slim

# Install with provider support
RUN pip install mlflow-secrets-auth[vault,aws,azure]

# Copy application
COPY . /app
WORKDIR /app

# Environment variables provided at runtime
ENV MLFLOW_SECRETS_AUTH_ENABLE=""
ENV VAULT_ADDR=""
ENV MLFLOW_VAULT_SECRET_PATH=""

CMD ["python", "app.py"]
```

**Runtime Configuration**:
```bash
docker run -e VAULT_ADDR="https://vault.company.com" \
           -e VAULT_TOKEN="$VAULT_TOKEN" \
           -e MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth" \
           -e MLFLOW_SECRETS_AUTH_ENABLE="vault" \
           mlflow-app
```

### How do I deploy in Kubernetes?

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
        - name: VAULT_TOKEN
          valueFrom:
            secretKeyRef:
              name: vault-auth
              key: token
        - name: MLFLOW_VAULT_SECRET_PATH
          value: "secret/mlflow/auth"
        - name: MLFLOW_SECRETS_AUTH_ENABLE
          value: "vault"
```

### How do I handle multiple environments?

Use environment-specific configuration:

```bash
#!/bin/bash
case "$ENVIRONMENT" in
  development)
    export VAULT_ADDR="http://localhost:8200"
    export MLFLOW_VAULT_SECRET_PATH="secret/dev/mlflow"
    export MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,*.local"
    ;;
  staging)
    export VAULT_ADDR="https://vault-staging.company.com"
    export MLFLOW_VAULT_SECRET_PATH="secret/staging/mlflow"
    export MLFLOW_SECRETS_ALLOWED_HOSTS="*.staging.company.com"
    ;;
  production)
    export VAULT_ADDR="https://vault.company.com"
    export MLFLOW_VAULT_SECRET_PATH="secret/prod/mlflow"
    export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
    ;;
esac
```

## Troubleshooting

### How do I debug authentication issues?

1. **Enable Debug Logging**:
   ```bash
   export MLFLOW_SECRETS_LOG_LEVEL=DEBUG
   mlflow-secrets-auth doctor
   ```

2. **Test Each Component**:
   ```bash
   # Test plugin status
   mlflow-secrets-auth info
   
   # Test provider connectivity
   mlflow-secrets-auth doctor
   
   # Test against MLflow server
   mlflow-secrets-auth doctor --dry-run https://mlflow.company.com
   ```

3. **Check Provider Access**:
   ```bash
   # Vault
   vault kv get secret/mlflow/auth
   
   # AWS
   aws secretsmanager get-secret-value --secret-id mlflow/auth
   
   # Azure
   az keyvault secret show --vault-name vault --name mlflow-auth
   ```

### Why isn't my secret being found?

Common causes:

1. **Wrong Path/Name**: Verify exact path or name
2. **Permissions**: Ensure read access to the secret
3. **Case Sensitivity**: Secret names are case-sensitive
4. **Provider Selection**: Verify correct provider is enabled and selected

Debug with:
```bash
# List available secrets
vault kv list secret/                              # Vault
aws secretsmanager list-secrets                    # AWS
az keyvault secret list --vault-name vault-name    # Azure
```

### Why is authentication slow?

Performance factors:

1. **Network Latency**: Distance to secret manager
2. **Cache Miss**: First request or expired cache
3. **Provider Performance**: Secret manager response time

Optimize with:
```bash
# Increase cache TTL
export MLFLOW_VAULT_TTL_SEC=1800  # 30 minutes

# Use regional endpoints
export AWS_REGION="us-east-1"  # Same region as application
```

### How do I verify the plugin is working?

1. **Check Plugin Status**:
   ```bash
   mlflow-secrets-auth info
   ```

2. **Monitor Network Traffic**: Should see HTTPS requests to secret managers

3. **Check MLflow Logs**: Should see authentication headers being added

4. **Test with Debug Mode**:
   ```bash
   MLFLOW_SECRETS_LOG_LEVEL=DEBUG python your_mlflow_script.py
   ```

## Migration and Integration

### How do I migrate from hardcoded credentials?

1. **Store Credentials in Secret Manager**:
   ```bash
   # Move from code/config files to secret manager
   vault kv put secret/mlflow/auth token="$EXISTING_TOKEN"
   ```

2. **Remove Hardcoded Values**:
   ```python
   # Before
   mlflow.set_tracking_uri("https://token:password@mlflow.company.com")
   
   # After (plugin handles authentication)
   mlflow.set_tracking_uri("https://mlflow.company.com")
   ```

3. **Configure Plugin**:
   ```bash
   export MLFLOW_SECRETS_AUTH_ENABLE="vault"
   export VAULT_ADDR="https://vault.company.com"
   export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
   ```

### Can I use this with existing MLflow authentication?

The plugin works alongside MLflow's existing authentication mechanisms:

1. **Plugin First**: If enabled and configured, plugin provides authentication
2. **Fallback**: If plugin disabled/fails, MLflow uses its default authentication
3. **Override**: Plugin authentication takes precedence when available

### How do I test before full deployment?

1. **Staging Environment**: Test in staging with same configuration
2. **Gradual Rollout**: Enable for subset of applications first
3. **A/B Testing**: Run with and without plugin in parallel
4. **Dry Run Testing**: Use CLI dry-run mode extensively

```bash
# Test without affecting production
mlflow-secrets-auth doctor --dry-run https://staging.mlflow.company.com
```

## Compatibility

### What MLflow versions are supported?

- **Minimum**: MLflow 2.20.4
- **Recommended**: Latest stable MLflow version
- **Compatibility**: Tested with MLflow 2.x series

### What Python versions are supported?

- **Supported**: Python 3.9, 3.10, 3.11, 3.12
- **Recommended**: Python 3.11 or higher
- **End of Life**: Python versions past EOL not supported

### Are there any known conflicts?

Generally compatible with:
- MLflow tracking, models, projects
- Other MLflow plugins
- Common Python web frameworks
- Cloud deployment platforms

Potential conflicts:
- Custom authentication plugins (first loaded wins)
- Applications that modify `requests.Session` globally
- Very old versions of provider SDKs

## Next Steps

- **[Getting Started](getting-started.md)** - Quick start guide
- **[Configuration Reference](configuration.md)** - Complete configuration options
- **[Troubleshooting Guide](troubleshooting.md)** - Detailed troubleshooting
- **[Provider Documentation](providers/)** - Provider-specific information

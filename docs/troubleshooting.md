# Troubleshooting

This guide covers common issues, diagnostic procedures, and solutions for MLflow Secrets Auth. Use this guide to resolve configuration problems, authentication failures, and performance issues.

## Quick Diagnostics

### Check Plugin Status

Start troubleshooting with basic status checks:

```bash
# Check plugin installation and configuration
mlflow-secrets-auth info

# Run comprehensive diagnostics
mlflow-secrets-auth doctor

# Test against specific MLflow server
mlflow-secrets-auth doctor --dry-run https://your-mlflow-server.com
```

### Enable Debug Logging

Enable detailed logging for troubleshooting:

```bash
export MLFLOW_SECRETS_LOG_LEVEL=DEBUG
mlflow-secrets-auth doctor
```

## Common Issues

### Plugin Not Recognized

#### Symptoms
- MLflow doesn't use authentication
- No authentication headers in requests
- Plugin appears inactive

#### Diagnosis
```bash
# Check if plugin is installed
pip show mlflow-secrets-auth

# Verify entry point registration
python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('mlflow.request_auth_provider'):
    print(f'{ep.name}: {ep.module_name}')
"

# Check if any provider is enabled
python -c "
from mlflow_secrets_auth.config import is_provider_enabled
providers = ['vault', 'aws-secrets-manager', 'azure-key-vault']
enabled = [p for p in providers if is_provider_enabled(p)]
print(f'Enabled providers: {enabled}')
"
```

#### Solutions
1. **Install the Plugin**:
   ```bash
   pip install mlflow-secrets-auth[vault,aws,azure]
   ```

2. **Enable a Provider**:
   ```bash
   export MLFLOW_SECRETS_AUTH_ENABLE="vault"
   # OR
   export MLFLOW_SECRETS_AUTH_ENABLE_VAULT=true
   ```

3. **Verify MLflow Version**:
   ```bash
   pip install "mlflow>=2.20.4"
   ```

### Authentication Failures

#### Symptoms
- "Authentication failed" errors
- 401/403 HTTP responses
- Secret retrieval failures

#### Provider-Specific Diagnosis

**Vault**:
```bash
# Test Vault connectivity
curl -k "$VAULT_ADDR/v1/sys/health"

# Check token validity
vault token lookup "$VAULT_TOKEN"

# Test secret access
vault kv get "$MLFLOW_VAULT_SECRET_PATH"
```

**AWS**:
```bash
# Check AWS credentials
aws sts get-caller-identity

# Test secret access
aws secretsmanager get-secret-value --secret-id "$MLFLOW_AWS_SECRET_NAME"

# Verify permissions
aws iam simulate-principal-policy \
  --policy-source-arn "$(aws sts get-caller-identity --query Arn --output text)" \
  --action-names "secretsmanager:GetSecretValue" \
  --resource-arns "arn:aws:secretsmanager:region:account:secret:$MLFLOW_AWS_SECRET_NAME-*"
```

**Azure**:
```bash
# Check Azure login
az account show

# Test Key Vault access
az keyvault secret show \
  --vault-name "vault-name" \
  --name "$MLFLOW_AZURE_SECRET_NAME"

# Check access policies
az keyvault show \
  --name "vault-name" \
  --query "properties.accessPolicies"
```

#### Solutions
1. **Verify Credentials**: Ensure authentication credentials are valid and not expired
2. **Check Permissions**: Verify the service has appropriate permissions to read secrets
3. **Test Connectivity**: Ensure network connectivity to the secret management service
4. **Validate Configuration**: Check all required environment variables are set

### Host Not Allowed

#### Symptoms
- "Host not allowed" errors
- Authentication works for some URLs but not others
- Wildcard patterns not matching expected hosts

#### Diagnosis
```bash
# Check current allowlist configuration
python -c "
from mlflow_secrets_auth.config import get_allowed_hosts
print(f'Allowed hosts: {get_allowed_hosts()}')
"

# Test host matching
python -c "
import fnmatch
from mlflow_secrets_auth.config import get_allowed_hosts
from urllib.parse import urlparse

url = 'https://your-server.com'
hostname = urlparse(url).hostname
allowed = get_allowed_hosts()

if allowed:
    matches = [pattern for pattern in allowed if fnmatch.fnmatch(hostname, pattern)]
    print(f'Host: {hostname}')
    print(f'Patterns: {allowed}')
    print(f'Matches: {matches}')
else:
    print('No host restrictions configured')
"
```

#### Solutions
1. **Add Host to Allowlist**:
   ```bash
   export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com,existing-hosts"
   ```

2. **Use Wildcard Patterns**:
   ```bash
   export MLFLOW_SECRETS_ALLOWED_HOSTS="*.company.com"
   ```

3. **Temporary Testing** (not recommended for production):
   ```bash
   unset MLFLOW_SECRETS_ALLOWED_HOSTS  # Allows all hosts
   ```

### Secret Not Found

#### Symptoms
- "Secret not found" errors
- Path or name not found messages
- Empty secret responses

#### Diagnosis
```bash
# List available secrets
# Vault
vault kv list secret/

# AWS
aws secretsmanager list-secrets

# Azure
az keyvault secret list --vault-name "your-vault"

# Check secret content
# Vault
vault kv get secret/path/to/secret

# AWS
aws secretsmanager get-secret-value --secret-id "secret-name"

# Azure
az keyvault secret show --vault-name "vault" --name "secret-name"
```

#### Solutions
1. **Verify Secret Path/Name**: Ensure the path or name exactly matches the stored secret
2. **Check Secret Format**: Verify the secret contains expected fields (`token`, `username`, `password`)
3. **Validate Permissions**: Ensure read access to the specific secret
4. **Test Different Versions**: For AWS/Azure, try different secret versions

### Cache Issues

#### Symptoms
- Stale authentication credentials
- Authentication works intermittently
- Changes to secrets not reflected

#### Diagnosis
```bash
# Check cache status (future feature)
mlflow-secrets-auth info  # Shows cache hit rate

# Test with debug logging
MLFLOW_SECRETS_LOG_LEVEL=DEBUG mlflow-secrets-auth doctor
```

#### Solutions
1. **Clear Cache** (restart application):
   ```bash
   # Current: restart the application
   # Future: mlflow-secrets-auth cache clear
   ```

2. **Reduce TTL**:
   ```bash
   export MLFLOW_VAULT_TTL_SEC=60      # 1 minute
   export MLFLOW_AWS_TTL_SEC=60
   export MLFLOW_AZURE_TTL_SEC=60
   ```

3. **Force Cache Bust**: Authentication failures automatically clear cache

### Network Connectivity

#### Symptoms
- Connection timeouts
- DNS resolution failures
- SSL/TLS errors

#### Diagnosis
```bash
# Test basic connectivity
# Vault
curl -v "$VAULT_ADDR/v1/sys/health"

# AWS (test any AWS service)
aws sts get-caller-identity

# Azure
curl -v "https://vault-name.vault.azure.net/"

# Check DNS resolution
nslookup vault.company.com
nslookup secretsmanager.us-east-1.amazonaws.com
nslookup vault-name.vault.azure.net

# Test SSL/TLS
openssl s_client -connect vault.company.com:443 -servername vault.company.com
```

#### Solutions
1. **Verify Network Access**: Ensure outbound connectivity to required endpoints
2. **Check Firewall Rules**: Verify firewall allows HTTPS traffic
3. **Validate DNS**: Ensure DNS resolution works for the secret management service
4. **Certificate Issues**: For Vault, consider `VAULT_SKIP_VERIFY=true` for testing (not production)

### Configuration Errors

#### Symptoms
- Missing environment variable errors
- Invalid configuration warnings
- Unexpected default values

#### Diagnosis
```bash
# Check all environment variables
env | grep -E "(VAULT_|AWS_|AZURE_|MLFLOW_SECRETS_)"

# Validate configuration
mlflow-secrets-auth info
```

#### Solutions
1. **Set Required Variables**: Ensure all required environment variables are set
2. **Check Variable Names**: Verify correct spelling and format of environment variables
3. **Validate Values**: Ensure values are in the expected format (URLs, regions, etc.)

## Performance Issues

### Slow Secret Retrieval

#### Symptoms
- Long delays in authentication
- Timeouts during secret fetching
- Poor application performance

#### Diagnosis
```bash
# Time secret retrieval
time mlflow-secrets-auth doctor

# Check network latency
ping vault.company.com
ping secretsmanager.us-east-1.amazonaws.com
```

#### Solutions
1. **Optimize TTL**: Increase cache TTL for better performance:
   ```bash
   export MLFLOW_VAULT_TTL_SEC=1800    # 30 minutes
   ```

2. **Use Regional Endpoints**: Ensure using the closest regional endpoint
3. **Network Optimization**: Use VPC endpoints, private networking
4. **Connection Pooling**: The plugin automatically reuses connections

### High Memory Usage

#### Symptoms
- Excessive memory consumption
- Memory leaks over time
- Out of memory errors

#### Diagnosis
```bash
# Monitor memory usage
ps aux | grep python
top -p $(pgrep -f mlflow)

# Check cache size (future feature)
# mlflow-secrets-auth cache status
```

#### Solutions
1. **Reduce Cache TTL**: Lower TTL reduces memory usage:
   ```bash
   export MLFLOW_VAULT_TTL_SEC=300     # 5 minutes
   ```

2. **Monitor Cache**: Restart applications periodically if needed
3. **Update Plugin**: Ensure using the latest version with memory optimizations

## Environment-Specific Issues

### Development Environment

#### Common Issues
- Local secret managers not configured
- Development certificates/tokens
- Network access restrictions

#### Solutions
```bash
# Use local Vault for development
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="dev-only-token"
export MLFLOW_VAULT_SECRET_PATH="secret/dev/mlflow"

# Disable host restrictions for development
export MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,127.0.0.1,*.local"

# Enable debug logging
export MLFLOW_SECRETS_LOG_LEVEL="DEBUG"
```

### CI/CD Environment

#### Common Issues
- Missing environment variables
- Temporary credentials
- Build pipeline failures

#### Solutions
```bash
# Validate configuration in CI
mlflow-secrets-auth doctor
if [ $? -ne 0 ]; then
    echo "MLflow Secrets Auth configuration failed"
    exit 1
fi

# Use short TTL in CI
export MLFLOW_VAULT_TTL_SEC=60

# Test against staging environment
mlflow-secrets-auth doctor --dry-run "$STAGING_MLFLOW_URL"
```

### Production Environment

#### Common Issues
- Credential rotation
- High availability requirements
- Security restrictions

#### Solutions
```bash
# Use appropriate TTL for production
export MLFLOW_VAULT_TTL_SEC=900     # 15 minutes

# Enable appropriate logging level
export MLFLOW_SECRETS_LOG_LEVEL="WARNING"

# Use production-grade allowlisting
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"

# Monitor authentication failures
# (Set up alerting on authentication errors)
```

## Provider-Specific Troubleshooting

### Vault Troubleshooting

#### KV Version Issues
```bash
# Check KV engine version
vault secrets list -detailed | grep secret

# Test both KV v1 and v2 paths
vault kv get secret/mlflow/auth          # KV v2
vault read secret/mlflow/auth            # KV v1
```

#### AppRole Issues
```bash
# Test AppRole login
vault write auth/approle/login \
  role_id="$VAULT_ROLE_ID" \
  secret_id="$VAULT_SECRET_ID"

# Check role configuration
vault read auth/approle/role/mlflow-secrets-auth
```

### AWS Troubleshooting

#### IAM Issues
```bash
# Check effective permissions
aws iam get-account-authorization-details

# Test assume role
aws sts assume-role \
  --role-arn "$AWS_ROLE_ARN" \
  --role-session-name "test-session"
```

#### Cross-Region Issues
```bash
# List secrets in different regions
aws secretsmanager list-secrets --region us-east-1
aws secretsmanager list-secrets --region us-west-2
```

### Azure Troubleshooting

#### Managed Identity Issues
```bash
# Test managed identity from Azure VM
curl -H "Metadata:true" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://vault.azure.net/"
```

#### RBAC vs Access Policy
```bash
# Check if RBAC is enabled
az keyvault show --name "vault-name" --query "properties.enableRbacAuthorization"

# List RBAC assignments
az role assignment list --assignee "$AZURE_CLIENT_ID"
```

## Advanced Debugging

### Packet Capture

For network-level debugging:

```bash
# Capture HTTPS traffic (requires root)
sudo tcpdump -i any -w mlflow-auth.pcap host vault.company.com

# Analyze with Wireshark or tshark
tshark -r mlflow-auth.pcap -Y "ssl"
```

### Python Debugging

For code-level debugging:

```python
import logging
import mlflow_secrets_auth

# Enable debug logging for all components
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('mlflow_secrets_auth')
logger.setLevel(logging.DEBUG)

# Test provider directly
from mlflow_secrets_auth import SecretsAuthProviderFactory
factory = SecretsAuthProviderFactory()
auth = factory.get_request_auth("https://mlflow.company.com")
print(f"Auth object: {auth}")
```

### Logging Analysis

Understanding log output:

```
# Normal operation
INFO: Secret fetched successfully (provider=vault, cache_hit=false)
INFO: Authentication successful (provider=vault, auth_mode=bearer)

# Cache hits
DEBUG: Cache hit for key: vault:https://vault.company.com:secret/mlflow/auth
INFO: Secret fetched successfully (provider=vault, cache_hit=true)

# Errors
ERROR: Vault authentication failed: 403 Forbidden
WARNING: Host not allowed: external.example.com
ERROR: Secret not found at path: secret/wrong/path
```

## Getting Help

### Before Asking for Help

1. **Check the Logs**: Enable debug logging and review the output
2. **Run Diagnostics**: Use `mlflow-secrets-auth doctor`
3. **Test Components**: Test each component (network, auth, secrets) individually
4. **Review Configuration**: Double-check all environment variables
5. **Check Documentation**: Review provider-specific documentation

### Information to Include

When reporting issues, include:

1. **Plugin Version**: `pip show mlflow-secrets-auth`
2. **Python Version**: `python --version`
3. **MLflow Version**: `pip show mlflow`
4. **Environment**: Development/staging/production
5. **Provider**: Vault/AWS/Azure
6. **Configuration**: Relevant environment variables (redacted)
7. **Error Messages**: Full error messages and stack traces
8. **Debug Logs**: Output from debug logging
9. **Diagnostic Output**: Output from `mlflow-secrets-auth doctor`

### Useful Commands for Bug Reports

```bash
# Collect system information
echo "Plugin version:"
pip show mlflow-secrets-auth

echo "Python version:"
python --version

echo "MLflow version:"
pip show mlflow

echo "Environment variables:"
env | grep -E "(VAULT_|AWS_|AZURE_|MLFLOW_SECRETS_)" | sed 's/=.*/=***/'

echo "Diagnostic output:"
MLFLOW_SECRETS_LOG_LEVEL=DEBUG mlflow-secrets-auth doctor
```

## Prevention

### Best Practices for Avoiding Issues

1. **Test in Staging**: Always test configuration changes in staging first
2. **Monitor Logs**: Set up log monitoring for authentication failures
3. **Health Checks**: Implement health checks using the CLI
4. **Documentation**: Document your configuration and troubleshooting steps
5. **Regular Updates**: Keep the plugin and dependencies updated

### Monitoring and Alerting

```bash
# Health check script
#!/bin/bash
if ! mlflow-secrets-auth doctor > /dev/null 2>&1; then
    echo "ALERT: MLflow Secrets Auth health check failed"
    exit 1
fi

# Performance monitoring
#!/bin/bash
start_time=$(date +%s%N)
mlflow-secrets-auth doctor > /dev/null 2>&1
end_time=$(date +%s%N)
duration=$(( (end_time - start_time) / 1000000 ))  # milliseconds

if [ $duration -gt 5000 ]; then  # 5 seconds
    echo "ALERT: MLflow Secrets Auth response time: ${duration}ms"
fi
```

### Configuration Validation

```bash
#!/bin/bash
# Configuration validation script

required_vars=()
case "$MLFLOW_SECRETS_AUTH_ENABLE" in
    *vault*)
        required_vars+=("VAULT_ADDR" "MLFLOW_VAULT_SECRET_PATH")
        ;;
    *aws-secrets-manager*)
        required_vars+=("AWS_REGION" "MLFLOW_AWS_SECRET_NAME")
        ;;
    *azure-key-vault*)
        required_vars+=("MLFLOW_AZURE_KEY_VAULT_URL" "MLFLOW_AZURE_SECRET_NAME")
        ;;
esac

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: Required variable $var is not set"
        exit 1
    fi
done

echo "Configuration validation passed"
```

## Next Steps

- **[CLI Reference](cli.md)** - Command-line tools for diagnostics
- **[Configuration Reference](configuration.md)** - Complete configuration options
- **[Provider Documentation](providers/)** - Provider-specific troubleshooting
- **[FAQ](faq.md)** - Frequently asked questions and answers

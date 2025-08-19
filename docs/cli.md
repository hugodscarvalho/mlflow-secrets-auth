# CLI Reference

The MLflow Secrets Auth CLI provides utilities for configuration validation, diagnostics, and troubleshooting. All commands support comprehensive logging and error reporting.

## Overview

The CLI tool is automatically installed with the plugin and provides two main commands:

- `info` - Display plugin version, configuration, and provider status
- `doctor` - Run comprehensive diagnostics and optional dry-run testing

## Installation

The CLI is available after installing the plugin:

```bash
pip install mlflow-secrets-auth[vault]
mlflow-secrets-auth --help
```

## Commands

### info

Display plugin information, version, and current configuration snapshot.

#### Usage

```bash
mlflow-secrets-auth info
```

#### Output

The `info` command displays:

- Plugin version and installation status
- Enabled providers and their availability
- Current configuration summary (with sensitive data redacted)
- Cache status and statistics
- Security settings (allowed hosts, auth header)

#### Example Output

```
MLflow Secrets Auth – Info
==========================

Version: 0.1.0
Installation: Package installed

Providers:
✓ vault: Enabled and available
✗ aws-secrets-manager: Disabled
✗ azure-key-vault: Disabled

Configuration:
  Auth Mode: bearer
  Auth Header: Authorization
  Cache TTL: 300 seconds
  Allowed Hosts: *.company.com, localhost

Cache Status:
  Entries: 1
  Hit Rate: 85.2%
  
Security:
  Host Allowlisting: Enabled
  Credential Redaction: Enabled
```

#### Exit Codes

- `0` - Success
- `1` - Plugin not properly installed or configured

### doctor

Run comprehensive diagnostics against the configured provider with optional dry-run testing.

#### Usage

```bash
mlflow-secrets-auth doctor [OPTIONS]
```

#### Options

- `--dry-run URL` - Test authentication against the specified MLflow tracking URL

#### Diagnostic Steps

The `doctor` command performs the following checks:

1. **Provider Resolution** - Identifies and validates the active provider
2. **Configuration Validation** - Checks all required environment variables
3. **Authentication Test** - Verifies provider credentials and connectivity
4. **Secret Retrieval** - Tests secret fetching and parsing
5. **Auth Construction** - Validates authentication header creation
6. **Dry-Run Test** (optional) - Tests against actual MLflow server

#### Example Usage

```bash
# Basic diagnostics
mlflow-secrets-auth doctor

# Test against specific MLflow server
mlflow-secrets-auth doctor --dry-run https://mlflow.company.com

# Debug mode with verbose output
MLFLOW_SECRETS_LOG_LEVEL=DEBUG mlflow-secrets-auth doctor
```

#### Example Output

```
MLflow Secrets Auth – Doctor
============================

✓ Provider Resolution
  Active Provider: vault
  Provider Status: Enabled and configured

✓ Configuration Validation
  Vault Address: https://vault.company.com
  Auth Mode: bearer
  Secret Path: secret/mlflow/auth
  TTL: 300 seconds
  Allowed Hosts: *.company.com

✓ Authentication Test
  Connection: Successful
  Authentication: Valid token
  Permissions: Read access confirmed

✓ Secret Retrieval
  Secret Found: Yes
  Secret Format: Valid JSON
  Required Fields: token (present)

✓ Auth Construction
  Header Name: Authorization
  Header Format: Bearer ****...****
  Auth Object: Valid

✓ Dry-Run Test (https://mlflow.company.com)
  Host Check: mlflow.company.com allowed
  Connection: Successful
  Auth Header: Applied correctly
  Response: 200 OK

All checks passed! ✓
```

#### Exit Codes

- `0` - All diagnostics passed
- `1` - One or more diagnostic checks failed

#### Failure Examples

**Provider Not Enabled**:
```
✗ Provider Resolution
  Error: No providers enabled
  Solution: Set MLFLOW_SECRETS_AUTH_ENABLE environment variable
```

**Authentication Failed**:
```
✗ Authentication Test
  Error: Vault authentication failed
  Details: Invalid token or expired
  Solution: Check VAULT_TOKEN or VAULT_ROLE_ID/VAULT_SECRET_ID
```

**Secret Not Found**:
```
✗ Secret Retrieval
  Error: Secret not found at path: secret/mlflow/auth
  Solution: Verify secret exists and path is correct
```

**Host Not Allowed**:
```
✗ Dry-Run Test (https://external.example.com)
  Error: Host not in allowlist
  Host: external.example.com
  Allowed: *.company.com, localhost
  Solution: Add host to MLFLOW_SECRETS_ALLOWED_HOSTS
```

## Global Options

### Logging

Control CLI output verbosity:

```bash
# Debug level logging
MLFLOW_SECRETS_LOG_LEVEL=DEBUG mlflow-secrets-auth doctor

# Quiet mode (errors only)
MLFLOW_SECRETS_LOG_LEVEL=ERROR mlflow-secrets-auth info

# Default: INFO level
mlflow-secrets-auth doctor
```

### Configuration Override

Test different configurations without modifying environment:

```bash
# Test with different provider
MLFLOW_SECRETS_AUTH_ENABLE=aws-secrets-manager mlflow-secrets-auth doctor

# Test with different secret path
MLFLOW_VAULT_SECRET_PATH=secret/test/auth mlflow-secrets-auth doctor

# Test with different allowed hosts
MLFLOW_SECRETS_ALLOWED_HOSTS=test.example.com mlflow-secrets-auth doctor --dry-run https://test.example.com
```

## Use Cases

### Development Workflow

```bash
# 1. Initial setup validation
mlflow-secrets-auth info

# 2. Test provider configuration
mlflow-secrets-auth doctor

# 3. Validate against development server
mlflow-secrets-auth doctor --dry-run http://localhost:5000

# 4. Debug connection issues
MLFLOW_SECRETS_LOG_LEVEL=DEBUG mlflow-secrets-auth doctor --dry-run http://localhost:5000
```

### CI/CD Integration

```bash
#!/bin/bash
# CI/CD pipeline validation script

echo "Validating MLflow Secrets Auth configuration..."

# Check plugin installation
if ! mlflow-secrets-auth info > /dev/null 2>&1; then
    echo "❌ Plugin not properly installed"
    exit 1
fi

# Run diagnostics
if ! mlflow-secrets-auth doctor; then
    echo "❌ Configuration validation failed"
    exit 1
fi

# Test against staging environment
if ! mlflow-secrets-auth doctor --dry-run "$MLFLOW_TRACKING_URI"; then
    echo "❌ Staging environment test failed"
    exit 1
fi

echo "✅ All validation checks passed"
```

### Production Monitoring

```bash
#!/bin/bash
# Health check script for production

# Set monitoring-friendly output
export MLFLOW_SECRETS_LOG_LEVEL=ERROR

# Quick configuration check
if mlflow-secrets-auth info > /dev/null 2>&1; then
    echo "HEALTHY: Plugin configuration valid"
else
    echo "UNHEALTHY: Plugin configuration invalid"
    exit 1
fi

# Test secret retrieval
if mlflow-secrets-auth doctor > /dev/null 2>&1; then
    echo "HEALTHY: Secret retrieval working"
else
    echo "UNHEALTHY: Secret retrieval failed"
    exit 1
fi
```

### Troubleshooting Workflow

```bash
# Step 1: Check basic configuration
mlflow-secrets-auth info

# Step 2: Enable debug logging and run diagnostics
MLFLOW_SECRETS_LOG_LEVEL=DEBUG mlflow-secrets-auth doctor

# Step 3: Test specific scenarios
mlflow-secrets-auth doctor --dry-run https://problematic-server.com

# Step 4: Test with minimal configuration
MLFLOW_SECRETS_ALLOWED_HOSTS="*" mlflow-secrets-auth doctor --dry-run https://any-server.com
```

## Error Messages

### Common Error Patterns

#### Configuration Errors

```
Error: VAULT_ADDR environment variable is required
Solution: export VAULT_ADDR="https://vault.company.com"

Error: No providers enabled
Solution: export MLFLOW_SECRETS_AUTH_ENABLE="vault"

Error: Secret path not configured
Solution: export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
```

#### Authentication Errors

```
Error: Vault authentication failed
Details: 403 Forbidden
Solution: Check token permissions or use valid AppRole credentials

Error: AWS credentials not found
Solution: Configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

Error: Azure authentication failed
Details: AADSTS70002: Error validating credentials
Solution: Check AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET
```

#### Network Errors

```
Error: Connection timeout to vault.company.com
Solution: Check network connectivity and firewall rules

Error: Host not allowed: external.example.com
Solution: Add to MLFLOW_SECRETS_ALLOWED_HOSTS or verify URL

Error: SSL verification failed
Solution: Check TLS certificates or consider VAULT_SKIP_VERIFY (not recommended)
```

## Advanced Usage

### Custom Validation Scripts

Create custom validation scripts using the CLI:

```bash
#!/bin/bash
# custom-validation.sh

# Function to check specific provider
check_provider() {
    local provider=$1
    echo "Checking $provider provider..."
    
    if MLFLOW_SECRETS_AUTH_ENABLE=$provider mlflow-secrets-auth doctor; then
        echo "✅ $provider provider working"
        return 0
    else
        echo "❌ $provider provider failed"
        return 1
    fi
}

# Test all providers
providers=("vault" "aws-secrets-manager" "azure-key-vault")
failed=0

for provider in "${providers[@]}"; do
    if ! check_provider $provider; then
        ((failed++))
    fi
done

if [ $failed -eq 0 ]; then
    echo "All providers validated successfully"
else
    echo "$failed provider(s) failed validation"
    exit 1
fi
```

### Performance Testing

```bash
#!/bin/bash
# performance-test.sh

echo "Testing secret retrieval performance..."

# Warm up cache
mlflow-secrets-auth doctor > /dev/null 2>&1

# Time multiple retrievals
for i in {1..10}; do
    start_time=$(date +%s%N)
    mlflow-secrets-auth doctor > /dev/null 2>&1
    end_time=$(date +%s%N)
    duration=$(( (end_time - start_time) / 1000000 ))
    echo "Run $i: ${duration}ms"
done
```

## Integration Examples

### Docker Health Checks

```dockerfile
FROM python:3.11-slim

# Install plugin
RUN pip install mlflow-secrets-auth[vault]

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD mlflow-secrets-auth doctor || exit 1

# Your application
COPY . /app
WORKDIR /app
```

### Kubernetes Readiness Probe

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: mlflow-app
    image: mlflow-app:latest
    readinessProbe:
      exec:
        command:
        - /bin/sh
        - -c
        - mlflow-secrets-auth doctor
      initialDelaySeconds: 10
      periodSeconds: 30
```

### Monitoring Integration

```bash
#!/bin/bash
# monitoring-check.sh for Prometheus/monitoring systems

# Output metrics format
echo "# HELP mlflow_secrets_auth_status Plugin configuration status"
echo "# TYPE mlflow_secrets_auth_status gauge"

if mlflow-secrets-auth doctor > /dev/null 2>&1; then
    echo "mlflow_secrets_auth_status 1"
else
    echo "mlflow_secrets_auth_status 0"
fi
```

## Next Steps

- **[Configuration Reference](configuration.md)** - Complete environment variable reference
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions
- **[Provider Documentation](providers/)** - Provider-specific configuration
- **[Security Best Practices](concepts/security.md)** - Security guidelines and recommendations

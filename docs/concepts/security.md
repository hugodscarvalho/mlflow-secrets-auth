# Security

MLflow Secrets Auth implements a comprehensive security model designed to protect credentials and prevent unauthorized access while maintaining usability and performance.

## Threat Model

### Assets

**Primary Assets**:
- Authentication credentials (tokens, passwords, API keys)
- Secret management system access
- MLflow server access
- Application configuration

**Secondary Assets**:
- Network communications
- Cache contents
- Log data
- System configuration

### Threats

#### Credential Exposure

**T1: Credential Leakage**
- **Description**: Credentials sent to unauthorized servers
- **Impact**: Unauthorized access to MLflow servers
- **Mitigation**: Host allowlisting, URL validation

**T2: Log Exposure**
- **Description**: Credentials visible in application logs
- **Impact**: Credential compromise through log access
- **Mitigation**: Automatic credential redaction

**T3: Memory Dumps**
- **Description**: Credentials visible in process memory dumps
- **Impact**: Credential extraction from memory
- **Mitigation**: Secure memory handling, limited credential lifetime

#### Network Attacks

**T4: Man-in-the-Middle**
- **Description**: Interception of credential transmission
- **Impact**: Credential theft during network transit
- **Mitigation**: TLS enforcement, certificate validation

**T5: DNS Poisoning**
- **Description**: Redirection to malicious servers
- **Impact**: Credentials sent to attacker-controlled servers
- **Mitigation**: Host allowlisting with exact hostnames

#### Configuration Attacks

**T6: Environment Variable Exposure**
- **Description**: Exposure of configuration through environment variables
- **Impact**: Access to secret paths and authentication parameters
- **Mitigation**: Principle of least privilege, secure configuration management

**T7: Cache Poisoning**
- **Description**: Injection of malicious credentials into cache
- **Impact**: Use of compromised credentials
- **Mitigation**: Cache integrity validation, TTL limits

## Security Controls

### Host Allowlisting

Host allowlisting is the primary defense against credential leakage to unauthorized servers.

#### Implementation

```python
def _is_host_allowed(self, hostname: str) -> bool:
    """Validate hostname against allowlist patterns."""
    allowed_hosts = get_allowed_hosts()
    if not allowed_hosts:
        return True  # No restrictions if not configured
    
    return any(
        fnmatch.fnmatch(hostname, pattern)
        for pattern in allowed_hosts
    )
```

#### Configuration Patterns

**Exact Hostnames**:
```bash
MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com,mlflow-staging.company.com"
```

**Wildcard Patterns**:
```bash
# Subdomain wildcards
MLFLOW_SECRETS_ALLOWED_HOSTS="*.company.com"

# Prefix wildcards  
MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow-*"

# Complex patterns
MLFLOW_SECRETS_ALLOWED_HOSTS="*.prod.company.com,*.staging.company.com,localhost"
```

#### Security Considerations

- **Default Behavior**: If not configured, allows all hosts (development-friendly but insecure)
- **Wildcard Risks**: Overly broad patterns can allow unintended hosts
- **Pattern Validation**: Patterns are validated using shell-style globbing
- **Case Sensitivity**: Hostname matching is case-insensitive

#### Best Practices

1. **Always Enable in Production**:
   ```bash
   MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
   ```

2. **Use Specific Patterns**:
   ```bash
   # Good: Specific subdomain
   MLFLOW_SECRETS_ALLOWED_HOSTS="*.mlflow.company.com"
   
   # Avoid: Too broad
   MLFLOW_SECRETS_ALLOWED_HOSTS="*.com"
   ```

3. **Environment-Specific Configuration**:
   ```bash
   # Development
   MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,127.0.0.1,*.local"
   
   # Staging
   MLFLOW_SECRETS_ALLOWED_HOSTS="*.staging.company.com"
   
   # Production
   MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
   ```

### Credential Redaction

All sensitive data is automatically redacted from logs and error messages to prevent accidental exposure.

#### Redaction Patterns

The system recognizes and redacts common credential patterns:

```python
_REDACT_PATTERNS = [
    # Bearer tokens: "Bearer <token>"
    re.compile(r"(Bearer\s+)([A-Za-z0-9._\-]+)"),
    
    # Basic auth: "Basic <b64>"
    re.compile(r"(Basic\s+)([A-Za-z0-9+/=]+)"),
    
    # JWT tokens
    re.compile(r"(eyJ[A-Za-z0-9._\-]+\.[A-Za-z0-9._\-]+\.[A-Za-z0-9._\-]+)"),
    
    # JSON fields: "token" / "password" / "secret" / "key"
    re.compile(r'("(?:token|password|secret|key)"\s*:\s*")([^"]+)(")'),
    
    # URL credentials: https://user:pass@host
    re.compile(r"(https?://[^:]+:)([^@]+)(@)"),
]
```

#### Masking Strategy

Sensitive values are masked while preserving context:

```python
def mask_secret(value: str, mask_char: str = "*", show_chars: int = 4) -> str:
    """Mask secret while showing prefix/suffix for debugging."""
    if len(value) <= show_chars * 2:
        return mask_char * max(3, len(value))
    
    return f"{value[:show_chars]}{mask_char * 8}{value[-show_chars:]}"

# Example output: "abcd********1234"
```

#### Log Output Examples

**Before Redaction**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Secret data: {"token": "abc123def456", "password": "secret123"}
```

**After Redaction**:
```
Authorization: Bearer eyJh********cCI6
Secret data: {"token": "abc1********def4", "password": "secr********123"}
```

### Secure Caching

The caching layer implements security measures to protect cached credentials.

#### Cache Security Features

**In-Memory Only**:
- No persistence to disk or external storage
- Automatic cleanup on process termination
- Memory-only storage prevents credential recovery

**TTL Enforcement**:
```python
class CacheEntry:
    def __init__(self, data: dict, ttl: int):
        self.data = data
        self.expiry = time.time() + ttl
    
    def is_expired(self) -> bool:
        return time.time() > self.expiry
```

**Cache Isolation**:
- Per-configuration cache keys prevent cross-contamination
- Different providers maintain separate cache spaces
- Cache keys include provider-specific identifiers

**Automatic Cache Busting**:
```python
def _handle_auth_failure(self, response: requests.Response):
    """Clear cache on authentication failure."""
    if response.status_code in (401, 403):
        cache_key = self._get_cache_key()
        self._cache.delete(cache_key)
        logger.info("Cache cleared due to authentication failure")
```

#### Cache Security Best Practices

1. **Appropriate TTL Values**:
   ```bash
   # Short TTL for high-security environments
   MLFLOW_VAULT_TTL_SEC=300  # 5 minutes
   
   # Longer TTL for development
   MLFLOW_VAULT_TTL_SEC=3600  # 1 hour
   ```

2. **Regular Cache Rotation**:
   ```python
   # Automatic rotation based on TTL
   # Manual rotation via cache busting on failures
   ```

3. **Memory Protection**:
   - Use memory-mapped regions when available
   - Implement secure memory wiping (platform-dependent)
   - Limit cache size to prevent memory exhaustion

### Network Security

#### TLS Enforcement

All communications with secret management systems use TLS by default:

```python
# Vault
VAULT_ADDR="https://vault.company.com"  # HTTPS required

# AWS
# TLS enforced by boto3 by default

# Azure  
# TLS enforced by Azure SDK by default
```

#### Certificate Validation

Certificate validation is enabled by default with options for testing:

```bash
# Production: Always validate certificates
VAULT_SKIP_VERIFY=false

# Development: May skip validation (NOT recommended)
VAULT_SKIP_VERIFY=true
```

#### Network Timeouts

Reasonable timeouts prevent hanging connections:

```python
# Default timeouts
NETWORK_TIMEOUT = 30  # seconds
CONNECT_TIMEOUT = 10  # seconds
READ_TIMEOUT = 20     # seconds
```

### Authentication Security

#### Provider-Specific Security

**HashiCorp Vault**:
- Token-based authentication with expiration
- AppRole authentication for automation
- Policy-based access control
- Audit logging support

```bash
# Vault policy example
path "secret/data/mlflow/*" {
  capabilities = ["read"]
}
```

**AWS Secrets Manager**:
- IAM-based access control
- Cross-account access via roles
- Resource-based policies
- CloudTrail audit logging

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue"],
    "Resource": "arn:aws:secretsmanager:region:account:secret:mlflow/*"
  }]
}
```

**Azure Key Vault**:
- Azure AD authentication
- Managed identity support
- Role-based access control (RBAC)
- Activity logging support

```bash
# Key Vault access policy
az keyvault set-policy \
  --name vault-name \
  --object-id user-id \
  --secret-permissions get
```

#### Credential Rotation

The plugin supports credential rotation through cache invalidation:

1. **Automatic Detection**: Authentication failures trigger cache clearing
2. **Manual Rotation**: CLI commands can clear cache
3. **TTL-Based Rotation**: Regular cache expiration forces re-fetch

```bash
# Manual cache clearing (future feature)
mlflow-secrets-auth cache clear

# TTL-based rotation
MLFLOW_VAULT_TTL_SEC=300  # Rotate every 5 minutes
```

### Principle of Least Privilege

#### IAM Permissions

**Vault Example**:
```hcl
# Minimal Vault policy
path "secret/data/mlflow/auth" {
  capabilities = ["read"]
}
```

**AWS Example**:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue"],
    "Resource": ["arn:aws:secretsmanager:us-east-1:123456789012:secret:mlflow/auth-*"],
    "Condition": {
      "StringEquals": {
        "secretsmanager:ResourceTag/Environment": "production"
      }
    }
  }]
}
```

**Azure Example**:
```bash
# Custom role with minimal permissions
az role definition create --role-definition '{
  "Name": "MLflow Secrets Reader",
  "Description": "Read MLflow secrets only",
  "Actions": [],
  "DataActions": [
    "Microsoft.KeyVault/vaults/secrets/getSecret/action"
  ],
  "AssignableScopes": ["/subscriptions/{subscription-id}"]
}'
```

#### Network Restrictions

1. **VPC/VNet Restrictions**: Limit access to secret managers from specific networks
2. **IP Allowlisting**: Configure secret managers to allow specific IP ranges
3. **Private Endpoints**: Use private connectivity when available

### Security Monitoring

#### Audit Logging

Enable audit logging on secret management systems:

**Vault**:
```bash
vault audit enable file file_path=/vault/logs/audit.log
```

**AWS**:
```bash
# CloudTrail automatically logs Secrets Manager access
```

**Azure**:
```bash
# Activity logs automatically capture Key Vault access
```

#### Application Logging

The plugin provides security-relevant logging:

```python
# Security events logged:
# - Authentication attempts
# - Host allowlist violations  
# - Cache operations
# - Configuration changes
# - Error conditions

logger.warning("Host not allowed: %s", hostname)
logger.info("Secret fetched successfully", extra={"provider": "vault"})
logger.error("Authentication failed", extra={"provider": "aws", "error_code": 403})
```

#### Monitoring Recommendations

1. **Failed Authentication Attempts**: Monitor for repeated failures
2. **Unusual Access Patterns**: Alert on access from unexpected sources
3. **Configuration Changes**: Track environment variable modifications
4. **Performance Anomalies**: Monitor secret fetch latency

### Security Testing

#### Security Validation

```bash
# Test host allowlisting
MLFLOW_SECRETS_ALLOWED_HOSTS="trusted.com" \
mlflow-secrets-auth doctor --dry-run https://untrusted.com

# Test credential redaction
MLFLOW_SECRETS_LOG_LEVEL=DEBUG mlflow-secrets-auth doctor

# Test authentication failure handling
# (Requires invalid credentials)
```

#### Penetration Testing Considerations

1. **Network Segmentation**: Test network-level restrictions
2. **Credential Validation**: Verify credential requirements
3. **Host Validation**: Test allowlist bypass attempts
4. **Cache Security**: Verify cache isolation and cleanup

## Security Compliance

### Standards Alignment

The plugin design aligns with common security standards:

- **NIST Cybersecurity Framework**: Identify, Protect, Detect, Respond, Recover
- **OWASP Top 10**: Addresses authentication and sensitive data exposure
- **SOC 2 Type II**: Supports security and availability controls
- **ISO 27001**: Implements information security management controls

### Compliance Features

1. **Data Classification**: Treats all credentials as sensitive data
2. **Access Controls**: Implements role-based access through secret managers
3. **Audit Trails**: Provides comprehensive logging for compliance reporting
4. **Encryption**: Uses TLS for data in transit, relies on secret managers for data at rest

## Security Best Practices

### Deployment Security

1. **Environment Isolation**:
   ```bash
   # Separate credentials per environment
   # Development
   MLFLOW_VAULT_SECRET_PATH="secret/dev/mlflow"
   
   # Production  
   MLFLOW_VAULT_SECRET_PATH="secret/prod/mlflow"
   ```

2. **Credential Rotation**:
   ```bash
   # Regular rotation schedule
   # Monitor expiration dates
   # Automate rotation where possible
   ```

3. **Network Security**:
   ```bash
   # Use private networks
   # Implement network segmentation
   # Enable TLS everywhere
   ```

4. **Monitoring and Alerting**:
   ```bash
   # Monitor authentication failures
   # Alert on unusual access patterns
   # Track configuration changes
   ```

### Development Security

1. **Secure Defaults**: Plugin defaults to secure configurations
2. **Developer Training**: Educate developers on security implications
3. **Code Review**: Include security review in development process
4. **Testing**: Include security testing in CI/CD pipelines

### Operational Security

1. **Regular Updates**: Keep plugin and dependencies updated
2. **Vulnerability Scanning**: Scan for known vulnerabilities
3. **Incident Response**: Have procedures for credential compromise
4. **Backup and Recovery**: Maintain secure backup procedures

## Next Steps

- **[Caching and Retries](caching-and-retries.md)** - Performance and reliability mechanisms
- **[Architecture](architecture.md)** - Overall system design and components
- **[Provider Documentation](../providers/)** - Provider-specific security considerations
- **[Troubleshooting](../troubleshooting.md)** - Security-related troubleshooting

# Azure Key Vault Provider

The Azure Key Vault provider enables MLflow Secrets Auth to retrieve credentials from Microsoft Azure Key Vault using Azure Active Directory authentication. It supports multiple Azure authentication methods and integrates seamlessly with Azure cloud services.

## Overview

Azure Key Vault is a cloud service for securely storing and accessing secrets, keys, and certificates. The MLflow Secrets Auth Azure provider integrates with Azure Active Directory (Azure AD) for authentication and supports various Azure deployment patterns.

### Features

- **Multiple Authentication Methods**: Service principals, managed identities, and certificate-based authentication
- **Azure AD Integration**: Native integration with Azure Active Directory
- **Managed Identity Support**: Seamless authentication for Azure-hosted applications
- **Certificate Authentication**: Support for certificate-based authentication
- **Multi-Cloud Support**: Works with Azure Government and other Azure clouds
- **Version Management**: Support for specific secret versions

### Requirements

- **Azure Subscription**: Valid Azure subscription with Key Vault access
- **Azure AD Permissions**: Appropriate Azure AD permissions for authentication
- **Key Vault Access**: Access policies or RBAC permissions for secret access
- **Network Access**: Connectivity to Azure Key Vault endpoints
- **Python Packages**: `azure-identity>=1.24.0`, `azure-keyvault-secrets>=4.10.0` (installed with `pip install mlflow-secrets-auth[azure]`)

## Installation

### Basic Installation

```bash
pip install mlflow-secrets-auth[azure]
```

### Verify Installation

```bash
python -c "import azure.identity, azure.keyvault.secrets; print('✓ Azure support available')"
```

## Authentication Methods

### Service Principal with Secret

Use Azure AD service principal with client secret for authentication.

#### Configuration

```bash
export AZURE_TENANT_ID="12345678-1234-1234-1234-123456789012"
export AZURE_CLIENT_ID="87654321-4321-4321-4321-210987654321"
export AZURE_CLIENT_SECRET="your-client-secret-value"
export MLFLOW_AZURE_KEY_VAULT_URL="https://your-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-auth"
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"
```

#### Service Principal Setup

1. **Create Service Principal**:
   ```bash
   az ad sp create-for-rbac \
     --name "mlflow-secrets-auth" \
     --role "Key Vault Secrets User" \
     --scopes "/subscriptions/{subscription-id}/resourceGroups/{rg-name}/providers/Microsoft.KeyVault/vaults/{vault-name}"
   ```

2. **Note Credentials**:
   ```json
   {
     "appId": "87654321-4321-4321-4321-210987654321",
     "displayName": "mlflow-secrets-auth",
     "password": "your-client-secret-value",
     "tenant": "12345678-1234-1234-1234-123456789012"
   }
   ```

### Service Principal with Certificate

Use certificate-based authentication for enhanced security.

#### Configuration

```bash
export AZURE_TENANT_ID="12345678-1234-1234-1234-123456789012"
export AZURE_CLIENT_ID="87654321-4321-4321-4321-210987654321"
export AZURE_CLIENT_CERTIFICATE_PATH="/path/to/certificate.pem"
export MLFLOW_AZURE_KEY_VAULT_URL="https://your-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-auth"
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"
```

#### Certificate Setup

1. **Generate Certificate**:
   ```bash
   openssl req -new -x509 -key private.key -out certificate.crt -days 365
   cat private.key certificate.crt > certificate.pem
   ```

2. **Upload to Service Principal**:
   ```bash
   az ad sp credential reset \
     --id "87654321-4321-4321-4321-210987654321" \
     --cert @certificate.crt
   ```

### Managed Identity (Recommended for Azure Services)

Use Azure Managed Identity for applications running on Azure services.

#### System-Assigned Managed Identity

```bash
export MLFLOW_AZURE_KEY_VAULT_URL="https://your-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-auth"
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"
# No Azure AD credentials needed - automatically detected
```

#### User-Assigned Managed Identity

```bash
export AZURE_CLIENT_ID="user-assigned-identity-client-id"
export MLFLOW_AZURE_KEY_VAULT_URL="https://your-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-auth"
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"
```

#### Managed Identity Setup

1. **Enable System-Assigned Identity**:
   ```bash
   az vm identity assign --name "my-vm" --resource-group "my-rg"
   ```

2. **Create User-Assigned Identity**:
   ```bash
   az identity create \
     --name "mlflow-identity" \
     --resource-group "my-rg"
   ```

3. **Assign to VM**:
   ```bash
   az vm identity assign \
     --name "my-vm" \
     --resource-group "my-rg" \
     --identities "/subscriptions/{subscription-id}/resourcegroups/{rg-name}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/mlflow-identity"
   ```

## Access Control

### Access Policies (Classic)

Traditional access policy model for Key Vault access.

#### Assign Access Policy

```bash
# Service principal access
az keyvault set-policy \
  --name "your-vault" \
  --spn "87654321-4321-4321-4321-210987654321" \
  --secret-permissions get

# Managed identity access
az keyvault set-policy \
  --name "your-vault" \
  --object-id "managed-identity-object-id" \
  --secret-permissions get
```

#### Access Policy JSON

```json
{
  "tenantId": "12345678-1234-1234-1234-123456789012",
  "objectId": "87654321-4321-4321-4321-210987654321",
  "permissions": {
    "secrets": ["get"]
  }
}
```

### RBAC (Recommended)

Role-Based Access Control for more granular permissions.

#### Enable RBAC

```bash
az keyvault update \
  --name "your-vault" \
  --resource-group "my-rg" \
  --enable-rbac-authorization true
```

#### Assign RBAC Role

```bash
# Service principal
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee "87654321-4321-4321-4321-210987654321" \
  --scope "/subscriptions/{subscription-id}/resourceGroups/{rg-name}/providers/Microsoft.KeyVault/vaults/{vault-name}"

# Managed identity
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee-object-id "managed-identity-object-id" \
  --assignee-principal-type ServicePrincipal \
  --scope "/subscriptions/{subscription-id}/resourceGroups/{rg-name}/providers/Microsoft.KeyVault/vaults/{vault-name}"
```

#### Custom RBAC Role

```json
{
  "Name": "MLflow Secrets Reader",
  "Description": "Read MLflow secrets from Key Vault",
  "Actions": [],
  "DataActions": [
    "Microsoft.KeyVault/vaults/secrets/getSecret/action"
  ],
  "NotActions": [],
  "NotDataActions": [],
  "AssignableScopes": [
    "/subscriptions/{subscription-id}"
  ]
}
```

## Secret Configuration

### Secret Creation

#### Using Azure CLI

```bash
# Create secret with value
az keyvault secret set \
  --vault-name "your-vault" \
  --name "mlflow-auth" \
  --value '{"token":"your-mlflow-token"}' \
  --tags Environment=production Application=mlflow
```

#### Using Azure Portal

1. Navigate to your Key Vault in Azure Portal
2. Select "Secrets" from the left menu
3. Click "Generate/Import"
4. Choose "Manual" upload type
5. Enter secret name: `mlflow-auth`
6. Enter secret value (JSON format)
7. Set expiration date (optional)
8. Add tags for organization

### Secret Naming Conventions

#### Hierarchical Naming

```bash
# Environment-based
mlflow-production-auth
mlflow-staging-auth
mlflow-development-auth

# Application-based
apps-mlflow-production-auth
apps-mlflow-staging-auth

# Team-based
team-data-science-mlflow-auth
team-ml-engineering-mlflow-auth
```

#### Resource-Specific Naming

```bash
# Resource group specific
export MLFLOW_AZURE_SECRET_NAME="mlflow-${RESOURCE_GROUP}-auth"

# Environment specific
export MLFLOW_AZURE_SECRET_NAME="mlflow-${ENVIRONMENT}-auth"
```

## Secret Format

### Bearer Token Authentication

Store the authentication token in a `token` field:

```bash
# Create secret with bearer token
az keyvault secret set \
  --vault-name "your-vault" \
  --name "mlflow-auth" \
  --value '{"token":"your-bearer-token"}'
```

**JSON Structure**:
```json
{
  "token": "your-bearer-token"
}
```

### Basic Authentication

Store username and password for Basic authentication:

```bash
# Create secret with basic auth
az keyvault secret set \
  --vault-name "your-vault" \
  --name "mlflow-auth" \
  --value '{"username":"mlflow-user","password":"secure-password"}'
```

**JSON Structure**:
```json
{
  "username": "mlflow-user",
  "password": "secure-password"
}
```

### Complex Secrets

Store additional metadata:

```bash
# Create secret with metadata
az keyvault secret set \
  --vault-name "your-vault" \
  --name "mlflow-auth" \
  --value '{"token":"bearer-token","description":"MLflow production auth","environment":"production"}' \
  --tags created_by=admin environment=production
```

**JSON Structure**:
```json
{
  "token": "bearer-token",
  "description": "MLflow production auth", 
  "environment": "production"
}
```

## Configuration Reference

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MLFLOW_AZURE_KEY_VAULT_URL` | Key Vault URL | `https://your-vault.vault.azure.net/` |
| `MLFLOW_AZURE_SECRET_NAME` | Secret name | `mlflow-auth` |

### Authentication Variables

#### Service Principal with Secret

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_TENANT_ID` | Azure AD tenant ID | `12345678-1234-1234-1234-123456789012` |
| `AZURE_CLIENT_ID` | Service principal client ID | `87654321-4321-4321-4321-210987654321` |
| `AZURE_CLIENT_SECRET` | Service principal secret | `your-client-secret` |

#### Service Principal with Certificate

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_TENANT_ID` | Azure AD tenant ID | `12345678-1234-1234-1234-123456789012` |
| `AZURE_CLIENT_ID` | Service principal client ID | `87654321-4321-4321-4321-210987654321` |
| `AZURE_CLIENT_CERTIFICATE_PATH` | Certificate file path | `/path/to/certificate.pem` |

#### Managed Identity

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_CLIENT_ID` | User-assigned identity client ID (optional) | `user-assigned-identity-client-id` |

### Optional Configuration

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `MLFLOW_AZURE_AUTH_MODE` | `bearer` | Authentication mode | `bearer`, `basic` |
| `MLFLOW_AZURE_TTL_SEC` | `300` | Cache TTL in seconds | `600` |
| `MLFLOW_AZURE_SECRET_VERSION` | `latest` | Secret version | `latest`, version ID |
| `AZURE_CLOUD_ENVIRONMENT` | `AzurePublicCloud` | Azure cloud environment | `AzurePublicCloud`, `AzureUSGovernment` |

## Examples

### Development Environment

```bash
#!/bin/bash
# Development setup with Azure Key Vault

# Azure AD configuration (service principal)
export AZURE_TENANT_ID="12345678-1234-1234-1234-123456789012"
export AZURE_CLIENT_ID="87654321-4321-4321-4321-210987654321"
export AZURE_CLIENT_SECRET="${DEV_AZURE_CLIENT_SECRET}"

# Azure Key Vault configuration
export MLFLOW_AZURE_KEY_VAULT_URL="https://dev-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-development-auth"
export MLFLOW_AZURE_AUTH_MODE="bearer"
export MLFLOW_AZURE_TTL_SEC="60"  # Short TTL for development
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"

# Security configuration
export MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,127.0.0.1,*.local"
export MLFLOW_SECRETS_LOG_LEVEL="DEBUG"

# Create development secret
az keyvault secret set \
  --vault-name "dev-vault" \
  --name "mlflow-development-auth" \
  --value '{"token":"dev-token-123"}'

# Test configuration
mlflow-secrets-auth doctor --dry-run http://localhost:5000
```

### Production Environment with Managed Identity

```bash
#!/bin/bash
# Production setup with managed identity

# Azure Key Vault configuration (no Azure AD credentials needed)
export MLFLOW_AZURE_KEY_VAULT_URL="https://prod-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-production-auth"
export MLFLOW_AZURE_AUTH_MODE="bearer"
export MLFLOW_AZURE_TTL_SEC="900"  # 15 minutes for production
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"

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
    export AZURE_TENANT_ID="${DEV_AZURE_TENANT_ID}"
    export AZURE_CLIENT_ID="${DEV_AZURE_CLIENT_ID}"
    export AZURE_CLIENT_SECRET="${DEV_AZURE_CLIENT_SECRET}"
    export MLFLOW_AZURE_KEY_VAULT_URL="https://dev-vault.vault.azure.net/"
    export MLFLOW_AZURE_SECRET_NAME="mlflow-dev-auth"
    export MLFLOW_AZURE_TTL_SEC="60"
    export MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,*.local"
    ;;
    
  staging)
    export AZURE_TENANT_ID="${STAGING_AZURE_TENANT_ID}"
    export AZURE_CLIENT_ID="${STAGING_AZURE_CLIENT_ID}"
    export AZURE_CLIENT_SECRET="${STAGING_AZURE_CLIENT_SECRET}"
    export MLFLOW_AZURE_KEY_VAULT_URL="https://staging-vault.vault.azure.net/"
    export MLFLOW_AZURE_SECRET_NAME="mlflow-staging-auth"
    export MLFLOW_AZURE_TTL_SEC="300"
    export MLFLOW_SECRETS_ALLOWED_HOSTS="*.staging.company.com"
    ;;
    
  production)
    # Using managed identity - no credentials needed
    export MLFLOW_AZURE_KEY_VAULT_URL="https://prod-vault.vault.azure.net/"
    export MLFLOW_AZURE_SECRET_NAME="mlflow-production-auth"
    export MLFLOW_AZURE_TTL_SEC="900"
    export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
    ;;
esac

export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"
mlflow-secrets-auth doctor
```

### Certificate-Based Authentication

```bash
#!/bin/bash
# Certificate-based authentication setup

# Azure AD configuration with certificate
export AZURE_TENANT_ID="12345678-1234-1234-1234-123456789012"
export AZURE_CLIENT_ID="87654321-4321-4321-4321-210987654321"
export AZURE_CLIENT_CERTIFICATE_PATH="/etc/ssl/certs/mlflow-auth.pem"

# Azure Key Vault configuration
export MLFLOW_AZURE_KEY_VAULT_URL="https://secure-vault.vault.azure.net/"
export MLFLOW_AZURE_SECRET_NAME="mlflow-secure-auth"
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"

# Validate certificate authentication
mlflow-secrets-auth doctor
```

## Version Management

### Secret Versions

Azure Key Vault maintains version history:

```bash
# Use latest version (default)
export MLFLOW_AZURE_SECRET_VERSION="latest"

# Use specific version
export MLFLOW_AZURE_SECRET_VERSION="d1234567890abcdef1234567890abcdef"
```

### Version Operations

```bash
# List secret versions
az keyvault secret list-versions --vault-name "your-vault" --name "mlflow-auth"

# Get specific version
az keyvault secret show \
  --vault-name "your-vault" \
  --name "mlflow-auth" \
  --version "d1234567890abcdef1234567890abcdef"

# Update secret (creates new version)
az keyvault secret set \
  --vault-name "your-vault" \
  --name "mlflow-auth" \
  --value '{"token":"updated-token"}'
```

## Azure Cloud Environments

### Government Cloud

```bash
# Azure US Government
export AZURE_CLOUD_ENVIRONMENT="AzureUSGovernment"
export MLFLOW_AZURE_KEY_VAULT_URL="https://your-vault.vault.usgovcloudapi.net/"
```

### China Cloud

```bash
# Azure China
export AZURE_CLOUD_ENVIRONMENT="AzureChinaCloud"
export MLFLOW_AZURE_KEY_VAULT_URL="https://your-vault.vault.azure.cn/"
```

## Troubleshooting

### Common Issues

#### Authentication Failures

**Problem**: `Azure authentication failed`

**Solutions**:

1. **Check Service Principal**:
   ```bash
   az login --service-principal \
     --username "$AZURE_CLIENT_ID" \
     --password "$AZURE_CLIENT_SECRET" \
     --tenant "$AZURE_TENANT_ID"
   ```

2. **Verify Managed Identity**:
   ```bash
   # From Azure VM
   curl -H "Metadata:true" "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://vault.azure.net/"
   ```

3. **Test Key Vault Access**:
   ```bash
   az keyvault secret show \
     --vault-name "your-vault" \
     --name "mlflow-auth"
   ```

#### Permission Errors

**Problem**: `Access denied to Key Vault`

**Solutions**:

1. **Check Access Policies**:
   ```bash
   az keyvault show --name "your-vault" --query "properties.accessPolicies"
   ```

2. **Verify RBAC Assignments**:
   ```bash
   az role assignment list \
     --assignee "$AZURE_CLIENT_ID" \
     --scope "/subscriptions/{subscription-id}/resourceGroups/{rg-name}/providers/Microsoft.KeyVault/vaults/{vault-name}"
   ```

3. **Test Permissions**:
   ```bash
   az keyvault secret list --vault-name "your-vault"
   ```

#### Network Connectivity

**Problem**: `Connection timeout to Key Vault`

**Solutions**:

1. **Test Connectivity**:
   ```bash
   curl "https://your-vault.vault.azure.net/"
   ```

2. **Check Private Endpoints**:
   ```bash
   az network private-endpoint list --resource-group "my-rg"
   ```

3. **Verify DNS Resolution**:
   ```bash
   nslookup your-vault.vault.azure.net
   ```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export MLFLOW_SECRETS_LOG_LEVEL="DEBUG"
mlflow-secrets-auth doctor
```

**Debug Output Includes**:
- Azure credential resolution chain
- Key Vault client configuration
- Authentication method selection
- API request/response details

### CLI Diagnostics

Use the CLI for comprehensive diagnostics:

```bash
# Basic configuration check
mlflow-secrets-auth info

# Full diagnostic with Azure connectivity
mlflow-secrets-auth doctor

# Test against MLflow server
mlflow-secrets-auth doctor --dry-run https://mlflow.company.com
```

## Security Best Practices

### Identity Security

1. **Use Managed Identities**: Prefer managed identities over service principals
2. **Principle of Least Privilege**: Grant minimal required permissions
3. **Certificate Authentication**: Use certificates instead of secrets when possible
4. **Regular Rotation**: Rotate service principal secrets regularly

### Network Security

1. **Private Endpoints**: Use private endpoints for enhanced security
2. **Virtual Network Integration**: Deploy Key Vault within VNet
3. **Firewall Rules**: Configure Key Vault firewall rules
4. **Network Security Groups**: Implement network-level controls

### Key Vault Security

1. **Soft Delete**: Enable soft delete for accidental deletion protection
2. **Purge Protection**: Enable purge protection for critical vaults
3. **Access Logging**: Enable diagnostic logging
4. **RBAC**: Use RBAC instead of access policies for new deployments

### Monitoring and Auditing

1. **Diagnostic Logs**:
   ```bash
   az monitor diagnostic-settings create \
     --name "keyvault-logs" \
     --resource "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault}" \
     --logs '[{"category":"AuditEvent","enabled":true}]' \
     --workspace "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.OperationalInsights/workspaces/{workspace}"
   ```

2. **Azure Monitor**: Set up alerts for unusual access patterns
3. **Security Center**: Monitor Key Vault recommendations
4. **Sentinel**: Integrate with Azure Sentinel for security analytics

## Integration Examples

### Azure Container Instances

```yaml
apiVersion: 2019-12-01
location: eastus
name: mlflow-app
properties:
  containers:
  - name: mlflow-app
    properties:
      image: mlflow-app:latest
      environmentVariables:
      - name: MLFLOW_AZURE_KEY_VAULT_URL
        value: https://prod-vault.vault.azure.net/
      - name: MLFLOW_AZURE_SECRET_NAME
        value: mlflow-production-auth
      - name: MLFLOW_SECRETS_AUTH_ENABLE
        value: azure-key-vault
      - name: MLFLOW_SECRETS_ALLOWED_HOSTS
        value: mlflow.company.com
  identity:
    type: UserAssigned
    userAssignedIdentities:
      /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/mlflow-identity: {}
```

### Azure App Service

```bash
#!/bin/bash
# Configure App Service with managed identity

# Enable system-assigned managed identity
az webapp identity assign \
  --name "mlflow-app" \
  --resource-group "my-rg"

# Configure environment variables
az webapp config appsettings set \
  --name "mlflow-app" \
  --resource-group "my-rg" \
  --settings \
    MLFLOW_AZURE_KEY_VAULT_URL="https://prod-vault.vault.azure.net/" \
    MLFLOW_AZURE_SECRET_NAME="mlflow-production-auth" \
    MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault" \
    MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
```

### Azure Functions

```json
{
  "version": "2.0",
  "functionApp": {
    "id": "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Web/sites/mlflow-functions"
  },
  "managedServiceIdentity": {
    "type": "SystemAssigned"
  },
  "applicationSettings": {
    "MLFLOW_AZURE_KEY_VAULT_URL": "https://prod-vault.vault.azure.net/",
    "MLFLOW_AZURE_SECRET_NAME": "mlflow-production-auth",
    "MLFLOW_SECRETS_AUTH_ENABLE": "azure-key-vault",
    "MLFLOW_SECRETS_ALLOWED_HOSTS": "mlflow.company.com"
  }
}
```

### Azure Kubernetes Service (AKS)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mlflow-app
  labels:
    aadpodidbinding: mlflow-identity
spec:
  containers:
  - name: mlflow-app
    image: mlflow-app:latest
    env:
    - name: MLFLOW_AZURE_KEY_VAULT_URL
      value: "https://prod-vault.vault.azure.net/"
    - name: MLFLOW_AZURE_SECRET_NAME
      value: "mlflow-production-auth"
    - name: MLFLOW_SECRETS_AUTH_ENABLE
      value: "azure-key-vault"
    - name: MLFLOW_SECRETS_ALLOWED_HOSTS
      value: "mlflow.company.com"
---
apiVersion: "aadpodidentity.k8s.io/v1"
kind: AzureIdentityBinding
metadata:
  name: mlflow-identity-binding
spec:
  AzureIdentity: mlflow-identity
  Selector: mlflow-identity
```

### Terraform Configuration

```hcl
# Create Key Vault
resource "azurerm_key_vault" "mlflow" {
  name                = "mlflow-vault"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id          = data.azurerm_client_config.current.tenant_id
  sku_name           = "standard"
  
  enable_rbac_authorization = true
  
  tags = {
    Environment = "production"
    Application = "mlflow"
  }
}

# Create secret
resource "azurerm_key_vault_secret" "mlflow_auth" {
  name         = "mlflow-production-auth"
  value        = jsonencode({
    token = var.mlflow_token
  })
  key_vault_id = azurerm_key_vault.mlflow.id
  
  tags = {
    Environment = "production"
    Application = "mlflow"
  }
}

# Create managed identity
resource "azurerm_user_assigned_identity" "mlflow" {
  name                = "mlflow-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Assign RBAC role
resource "azurerm_role_assignment" "mlflow_keyvault" {
  scope                = azurerm_key_vault.mlflow.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.mlflow.principal_id
}
```

## Next Steps

- **[HashiCorp Vault Provider](vault.md)** - Vault-specific configuration
- **[AWS Secrets Manager Provider](aws.md)** - AWS-specific configuration
- **[Configuration Reference](../configuration.md)** - Complete environment variable reference
- **[Troubleshooting Guide](../troubleshooting.md)** - General troubleshooting information

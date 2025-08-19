# AWS Secrets Manager Provider

The AWS Secrets Manager provider enables MLflow Secrets Auth to retrieve credentials from Amazon Web Services Secrets Manager using IAM authentication. It supports multiple AWS authentication methods and handles both SecretString and SecretBinary secret types.

## Overview

AWS Secrets Manager is a fully managed service that helps protect secrets needed to access applications, services, and IT resources. The MLflow Secrets Auth AWS provider integrates with AWS IAM for authentication and supports various AWS deployment patterns.

### Features

- **Multiple Authentication Methods**: IAM users, roles, instance profiles, and AssumeRole
- **Secret Type Support**: SecretString and SecretBinary handling
- **Version Management**: Support for specific secret versions and staging labels
- **Multi-Region Support**: Cross-region secret access
- **AWS Integration**: Native integration with AWS services and deployment patterns
- **Automatic Retries**: Built-in retry logic with AWS SDK retry configurations

### Requirements

- **AWS Account**: Valid AWS account with Secrets Manager access
- **IAM Permissions**: Appropriate IAM permissions for secret access
- **Network Access**: Connectivity to AWS Secrets Manager endpoints
- **Python Package**: `boto3>=1.40.11` (installed with `pip install mlflow-secrets-auth[aws]`)
- **AWS Credentials**: Valid AWS credentials via any supported method

## Installation

### Basic Installation

```bash
pip install mlflow-secrets-auth[aws]
```

### Verify Installation

```bash
python -c "import boto3; print('✓ AWS support available')"
```

## Authentication Methods

### IAM User Credentials

Use long-term IAM user credentials with access keys.

#### Configuration

```bash
export AWS_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="AKIAXXXXXXXXXXXXXXXX"
export AWS_SECRET_ACCESS_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export MLFLOW_AWS_SECRET_NAME="mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"
```

#### IAM User Setup

1. **Create IAM User**:
   ```bash
   aws iam create-user --user-name mlflow-secrets-auth
   ```

2. **Attach Policy**:
   ```bash
   aws iam attach-user-policy \
     --user-name mlflow-secrets-auth \
     --policy-arn arn:aws:iam::123456789012:policy/MLflowSecretsManagerRead
   ```

3. **Create Access Keys**:
   ```bash
   aws iam create-access-key --user-name mlflow-secrets-auth
   ```

### IAM Role (Recommended)

Use IAM roles for enhanced security and temporary credentials.

#### EC2 Instance Profile

For applications running on EC2 instances:

```bash
export AWS_REGION="us-east-1"
export MLFLOW_AWS_SECRET_NAME="mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"
# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY not needed
```

#### ECS Task Role

For applications running in ECS:

```json
{
  "family": "mlflow-app",
  "taskRoleArn": "arn:aws:iam::123456789012:role/MLflowTaskRole",
  "containerDefinitions": [{
    "name": "mlflow-app",
    "environment": [
      {"name": "AWS_REGION", "value": "us-east-1"},
      {"name": "MLFLOW_AWS_SECRET_NAME", "value": "mlflow/auth"},
      {"name": "MLFLOW_SECRETS_AUTH_ENABLE", "value": "aws-secrets-manager"}
    ]
  }]
}
```

#### Lambda Function Role

For applications running in AWS Lambda:

```bash
# Environment variables set in Lambda configuration
AWS_REGION=us-east-1
MLFLOW_AWS_SECRET_NAME=mlflow/auth
MLFLOW_SECRETS_AUTH_ENABLE=aws-secrets-manager
```

### AssumeRole

Use AssumeRole for cross-account access or enhanced security.

#### Configuration

```bash
export AWS_REGION="us-east-1"
export AWS_ROLE_ARN="arn:aws:iam::123456789012:role/MLflowSecretsRole"
export AWS_ROLE_SESSION_NAME="mlflow-secrets-session"
export MLFLOW_AWS_SECRET_NAME="mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"
```

#### Cross-Account Access

```bash
# Cross-account role assumption
export AWS_ROLE_ARN="arn:aws:iam::ANOTHER-ACCOUNT:role/MLflowSecretsRole"
export AWS_EXTERNAL_ID="unique-external-id"  # If required
```

### AWS Profiles

Use AWS CLI profiles for local development.

#### Configuration

```bash
export AWS_REGION="us-east-1"
export AWS_PROFILE="mlflow-profile"
export MLFLOW_AWS_SECRET_NAME="mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"
```

#### Profile Setup

```bash
# Configure AWS profile
aws configure --profile mlflow-profile
```

**Profile File (`~/.aws/credentials`)**:
```ini
[mlflow-profile]
aws_access_key_id = AKIAXXXXXXXXXXXXXXXX
aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
region = us-east-1
```

## IAM Permissions

### Basic Secret Access Policy

Minimal policy for reading secrets:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:mlflow/*"
      ]
    }
  ]
}
```

### Enhanced Security Policy

Policy with additional security controls:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:mlflow/auth-*"
      ],
      "Condition": {
        "StringEquals": {
          "secretsmanager:ResourceTag/Environment": "production",
          "secretsmanager:ResourceTag/Application": "mlflow"
        },
        "IpAddress": {
          "aws:SourceIp": ["10.0.0.0/16", "192.168.1.0/24"]
        }
      }
    }
  ]
}
```

### Cross-Account Access Policy

For cross-account secret access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole"
      ],
      "Resource": [
        "arn:aws:iam::TARGET-ACCOUNT:role/MLflowSecretsRole"
      ]
    }
  ]
}
```

**Target Account Role Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::SOURCE-ACCOUNT:role/SourceRole"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "unique-external-id"
        }
      }
    }
  ]
}
```

## Secret Configuration

### Secret Creation

#### Using AWS CLI

```bash
# Create secret with SecretString
aws secretsmanager create-secret \
  --name "mlflow/auth" \
  --description "MLflow authentication credentials" \
  --secret-string '{"token":"your-mlflow-token"}' \
  --tags '[{"Key":"Environment","Value":"production"},{"Key":"Application","Value":"mlflow"}]'
```

#### Using AWS Console

1. Navigate to AWS Secrets Manager
2. Choose "Store a new secret"
3. Select "Other type of secret"
4. Enter key-value pairs or JSON
5. Set secret name: `mlflow/auth`
6. Configure rotation (optional)
7. Add tags for organization

### Secret Naming

#### Hierarchical Naming

```bash
# Environment-based hierarchy
mlflow/production/auth
mlflow/staging/auth  
mlflow/development/auth

# Application-based hierarchy
apps/mlflow/production/auth
apps/mlflow/staging/auth

# Team-based hierarchy
teams/data-science/mlflow/auth
teams/ml-engineering/mlflow/auth
```

#### ARN-Based Reference

```bash
# Full ARN reference
export MLFLOW_AWS_SECRET_NAME="arn:aws:secretsmanager:us-east-1:123456789012:secret:mlflow/auth-AbCdEf"

# Cross-region reference
export MLFLOW_AWS_SECRET_NAME="arn:aws:secretsmanager:eu-west-1:123456789012:secret:mlflow/auth-XyZ123"
```

## Secret Format

### Bearer Token Authentication

Store the authentication token in a `token` field:

```bash
# Create secret with bearer token
aws secretsmanager create-secret \
  --name "mlflow/auth" \
  --secret-string '{"token":"your-bearer-token"}'
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
aws secretsmanager create-secret \
  --name "mlflow/auth" \
  --secret-string '{"username":"mlflow-user","password":"secure-password"}'
```

**JSON Structure**:
```json
{
  "username": "mlflow-user",
  "password": "secure-password"
}
```

### Binary Secrets

AWS Secrets Manager supports binary data:

```bash
# Store binary secret (base64 encoded)
aws secretsmanager create-secret \
  --name "mlflow/auth" \
  --secret-binary fileb://secret-file.bin
```

The provider automatically handles base64 encoding/decoding for binary secrets.

## Configuration Reference

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for Secrets Manager | `us-east-1` |
| `MLFLOW_AWS_SECRET_NAME` | Secret name or ARN | `mlflow/auth` |

### Authentication Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | IAM user access key | `AKIAXXXXXXXXXXXXXXXX` |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `AWS_SESSION_TOKEN` | Temporary session token | `IQoJb3JpZ...` |
| `AWS_PROFILE` | AWS CLI profile name | `mlflow-profile` |
| `AWS_ROLE_ARN` | Role ARN for AssumeRole | `arn:aws:iam::123456789012:role/MLflowRole` |
| `AWS_ROLE_SESSION_NAME` | AssumeRole session name | `mlflow-session` |
| `AWS_EXTERNAL_ID` | External ID for AssumeRole | `unique-external-id` |

### Optional Configuration

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `MLFLOW_AWS_AUTH_MODE` | `bearer` | Authentication mode | `bearer`, `basic` |
| `MLFLOW_AWS_TTL_SEC` | `300` | Cache TTL in seconds | `600` |
| `MLFLOW_AWS_SECRET_VERSION` | `AWSCURRENT` | Secret version | `AWSCURRENT`, `AWSPENDING` |
| `MLFLOW_AWS_MAX_RETRIES` | `3` | Maximum retry attempts | `5` |
| `MLFLOW_AWS_RETRY_MODE` | `adaptive` | Retry mode | `legacy`, `standard`, `adaptive` |

## Examples

### Development Environment

```bash
#!/bin/bash
# Development setup with AWS Secrets Manager

# AWS configuration
export AWS_REGION="us-east-1"
export AWS_PROFILE="mlflow-dev"

# MLflow Secrets Auth configuration
export MLFLOW_AWS_SECRET_NAME="mlflow/development/auth"
export MLFLOW_AWS_AUTH_MODE="bearer"
export MLFLOW_AWS_TTL_SEC="60"  # Short TTL for development
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"

# Security configuration
export MLFLOW_SECRETS_ALLOWED_HOSTS="localhost,127.0.0.1,*.local"
export MLFLOW_SECRETS_LOG_LEVEL="DEBUG"

# Create development secret
aws secretsmanager create-secret \
  --name "mlflow/development/auth" \
  --secret-string '{"token":"dev-token-123"}' \
  --profile mlflow-dev

# Test configuration
mlflow-secrets-auth doctor --dry-run http://localhost:5000
```

### Production Environment

```bash
#!/bin/bash
# Production setup with IAM role

# AWS configuration (using IAM role - no access keys needed)
export AWS_REGION="us-east-1"

# MLflow Secrets Auth configuration
export MLFLOW_AWS_SECRET_NAME="mlflow/production/auth"
export MLFLOW_AWS_AUTH_MODE="bearer"
export MLFLOW_AWS_TTL_SEC="900"  # 15 minutes for production
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"

# Security configuration
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"
export MLFLOW_SECRETS_LOG_LEVEL="INFO"

# Validate configuration
mlflow-secrets-auth doctor
```

### Multi-Region Setup

```bash
#!/bin/bash
# Multi-region configuration

PRIMARY_REGION="us-east-1"
BACKUP_REGION="us-west-2"

# Try primary region first
export AWS_REGION="$PRIMARY_REGION"
export MLFLOW_AWS_SECRET_NAME="mlflow/auth"

if mlflow-secrets-auth doctor > /dev/null 2>&1; then
    echo "Using primary region: $PRIMARY_REGION"
else
    echo "Primary region failed, switching to backup: $BACKUP_REGION"
    export AWS_REGION="$BACKUP_REGION"
    mlflow-secrets-auth doctor
fi
```

### Cross-Account Access

```bash
#!/bin/bash
# Cross-account secret access

# Source account credentials (initial authentication)
export AWS_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="$SOURCE_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$SOURCE_SECRET_KEY"

# Target account role (for secret access)
export AWS_ROLE_ARN="arn:aws:iam::TARGET-ACCOUNT:role/MLflowSecretsRole"
export AWS_ROLE_SESSION_NAME="mlflow-cross-account-$(date +%s)"
export AWS_EXTERNAL_ID="$EXTERNAL_ID"

# Secret configuration
export MLFLOW_AWS_SECRET_NAME="mlflow/shared/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"

# Test cross-account access
mlflow-secrets-auth doctor
```

## Version Management

### Secret Versions

AWS Secrets Manager maintains version history:

```bash
# Use current version (default)
export MLFLOW_AWS_SECRET_VERSION="AWSCURRENT"

# Use pending version (during rotation)
export MLFLOW_AWS_SECRET_VERSION="AWSPENDING"

# Use specific version ID
export MLFLOW_AWS_SECRET_VERSION="01234567-89ab-cdef-0123-456789abcdef"
```

### Secret Rotation

Configure automatic rotation:

```bash
# Create secret with rotation
aws secretsmanager create-secret \
  --name "mlflow/auth" \
  --secret-string '{"token":"initial-token"}' \
  --replica-regions Region=us-west-2 \
  --force-overwrite-replica-secret

# Configure rotation
aws secretsmanager rotate-secret \
  --secret-id "mlflow/auth" \
  --rotation-lambda-arn "arn:aws:lambda:us-east-1:123456789012:function:mlflow-token-rotator" \
  --rotation-rules AutomaticallyAfterDays=30
```

## Troubleshooting

### Common Issues

#### Authentication Failures

**Problem**: `AWS credentials not found`

**Solutions**:

1. **Check AWS Configuration**:
   ```bash
   aws sts get-caller-identity
   ```

2. **Verify IAM Permissions**:
   ```bash
   aws iam simulate-principal-policy \
     --policy-source-arn "arn:aws:iam::123456789012:user/mlflow-user" \
     --action-names "secretsmanager:GetSecretValue" \
     --resource-arns "arn:aws:secretsmanager:us-east-1:123456789012:secret:mlflow/auth-*"
   ```

3. **Test Secret Access**:
   ```bash
   aws secretsmanager get-secret-value --secret-id "mlflow/auth"
   ```

#### Secret Not Found

**Problem**: `Secret not found`

**Solutions**:

1. **List Available Secrets**:
   ```bash
   aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `mlflow`)]'
   ```

2. **Check Secret ARN**:
   ```bash
   aws secretsmanager describe-secret --secret-id "mlflow/auth"
   ```

3. **Verify Region**:
   ```bash
   aws secretsmanager list-secrets --region us-west-2
   ```

#### Network Connectivity

**Problem**: `Connection timeout`

**Solutions**:

1. **Test AWS Connectivity**:
   ```bash
   aws secretsmanager list-secrets --max-items 1
   ```

2. **Check VPC Endpoints**:
   ```bash
   aws ec2 describe-vpc-endpoints --filters Name=service-name,Values=com.amazonaws.region.secretsmanager
   ```

3. **Verify DNS Resolution**:
   ```bash
   nslookup secretsmanager.us-east-1.amazonaws.com
   ```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export MLFLOW_SECRETS_LOG_LEVEL="DEBUG"
mlflow-secrets-auth doctor
```

**Debug Output Includes**:
- AWS credential resolution
- Secret Manager client configuration
- API request/response details
- Error details and retry attempts

### CLI Diagnostics

Use the CLI for comprehensive diagnostics:

```bash
# Basic configuration check
mlflow-secrets-auth info

# Full diagnostic with AWS connectivity
mlflow-secrets-auth doctor

# Test against MLflow server
mlflow-secrets-auth doctor --dry-run https://mlflow.company.com
```

## Security Best Practices

### IAM Security

1. **Principle of Least Privilege**: Grant minimal required permissions
2. **Use IAM Roles**: Prefer roles over long-term access keys
3. **Regular Rotation**: Rotate access keys and secrets regularly
4. **Condition-Based Policies**: Use conditions to restrict access

### Network Security

1. **VPC Endpoints**: Use VPC endpoints for private connectivity
2. **Security Groups**: Restrict outbound access to AWS services
3. **PrivateLink**: Use AWS PrivateLink for enhanced security
4. **Network ACLs**: Implement network-level controls

### Secret Security

1. **Encryption in Transit**: HTTPS/TLS enforced by default
2. **Encryption at Rest**: AWS KMS encryption for stored secrets
3. **Access Logging**: Enable CloudTrail logging
4. **Secret Rotation**: Implement automatic rotation

### Monitoring and Auditing

1. **CloudTrail Logging**:
   ```json
   {
     "eventSource": "secretsmanager.amazonaws.com",
     "eventName": "GetSecretValue",
     "sourceIPAddress": "10.0.1.100",
     "userIdentity": {
       "type": "AssumedRole",
       "principalId": "AROAEXAMPLE:mlflow-session"
     }
   }
   ```

2. **CloudWatch Metrics**: Monitor secret access patterns
3. **AWS Config**: Track configuration compliance
4. **Security Hub**: Centralized security findings

## Performance Optimization

### Connection Reuse

The provider automatically reuses AWS client connections:

```python
# Connection pooling handled by boto3
# Sessions and clients are cached per provider instance
```

### Caching Strategy

Configure appropriate TTL based on your rotation frequency:

```bash
# High-frequency rotation: shorter TTL
MLFLOW_AWS_TTL_SEC=300   # 5 minutes

# Standard rotation: medium TTL
MLFLOW_AWS_TTL_SEC=900   # 15 minutes

# Infrequent rotation: longer TTL
MLFLOW_AWS_TTL_SEC=1800  # 30 minutes
```

### Regional Optimization

1. **Same Region**: Deploy in same region as Secrets Manager
2. **VPC Endpoints**: Use VPC endpoints to avoid internet routing
3. **Regional Replication**: Use secret replication for DR

## Integration Examples

### Docker Deployment

```dockerfile
FROM python:3.11-slim

# Install MLflow Secrets Auth with AWS support
RUN pip install mlflow-secrets-auth[aws]

# Copy application
COPY . /app
WORKDIR /app

# Environment variables will be provided at runtime
ENV AWS_REGION=""
ENV MLFLOW_AWS_SECRET_NAME=""
ENV MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"

# Use IAM role for authentication (no access keys in image)
CMD ["python", "app.py"]
```

### ECS Task Definition

```json
{
  "family": "mlflow-app",
  "taskRoleArn": "arn:aws:iam::123456789012:role/MLflowTaskRole",
  "executionRoleArn": "arn:aws:iam::123456789012:role/MLflowExecutionRole",
  "containerDefinitions": [
    {
      "name": "mlflow-app",
      "image": "mlflow-app:latest",
      "environment": [
        {"name": "AWS_REGION", "value": "us-east-1"},
        {"name": "MLFLOW_AWS_SECRET_NAME", "value": "mlflow/production/auth"},
        {"name": "MLFLOW_SECRETS_AUTH_ENABLE", "value": "aws-secrets-manager"},
        {"name": "MLFLOW_SECRETS_ALLOWED_HOSTS", "value": "mlflow.company.com"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mlflow-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Lambda Function

```python
import os
import mlflow

def lambda_handler(event, context):
    # Environment variables configured in Lambda
    # AWS_REGION=us-east-1
    # MLFLOW_AWS_SECRET_NAME=mlflow/auth
    # MLFLOW_SECRETS_AUTH_ENABLE=aws-secrets-manager
    
    mlflow.set_tracking_uri("https://mlflow.company.com")
    
    with mlflow.start_run():
        mlflow.log_param("lambda_function", context.function_name)
        mlflow.log_metric("invocation_count", 1)
    
    return {"statusCode": 200, "body": "Success"}
```

### Terraform Configuration

```hcl
# Create secret
resource "aws_secretsmanager_secret" "mlflow_auth" {
  name        = "mlflow/production/auth"
  description = "MLflow authentication credentials"
  
  tags = {
    Environment = "production"
    Application = "mlflow"
  }
}

resource "aws_secretsmanager_secret_version" "mlflow_auth" {
  secret_id = aws_secretsmanager_secret.mlflow_auth.id
  secret_string = jsonencode({
    token = var.mlflow_token
  })
}

# IAM role for ECS task
resource "aws_iam_role" "mlflow_task_role" {
  name = "MLflowTaskRole"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "mlflow_secrets_access" {
  name = "MLflowSecretsAccess"
  role = aws_iam_role.mlflow_task_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.mlflow_auth.arn]
      }
    ]
  })
}
```

## Next Steps

- **[Azure Key Vault Provider](azure.md)** - Azure-specific configuration
- **[HashiCorp Vault Provider](vault.md)** - Vault-specific configuration
- **[Configuration Reference](../configuration.md)** - Complete environment variable reference
- **[Troubleshooting Guide](../troubleshooting.md)** - General troubleshooting information

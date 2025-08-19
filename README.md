# MLflow Secrets Auth

A secure MLflow plugin that automatically injects authentication headers from secret management systems into tracking requests.

[![CI/CD Pipeline](https://github.com/hugodscarvalho/mlflow-secrets-auth/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/hugodscarvalho/mlflow-secrets-auth/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/hugodscarvalho/mlflow-secrets-auth/branch/main/graph/badge.svg)](https://codecov.io/gh/hugodscarvalho/mlflow-secrets-auth)
[![PyPI version](https://img.shields.io/pypi/v/mlflow-secrets-auth.svg)](https://pypi.org/project/mlflow-secrets-auth/)
[![Python versions](https://img.shields.io/pypi/pyversions/mlflow-secrets-auth.svg)](https://pypi.org/project/mlflow-secrets-auth/)
[![License](https://img.shields.io/github/license/hugodscarvalho/mlflow-secrets-auth.svg)](LICENSE)

## Features

- **Zero Code Changes**: Works transparently with existing MLflow applications
- **Multiple Providers**: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault
- **Security First**: Host allowlisting, credential redaction, in-memory caching only
- **Production Ready**: Automatic retries, TTL-based caching, comprehensive logging

## Quick Start

```bash
# Install with your preferred provider
pip install mlflow-secrets-auth[vault]

# Configure for HashiCorp Vault
export VAULT_ADDR="https://vault.company.com"
export VAULT_TOKEN="your-vault-token"
export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="vault"

# Your MLflow code works unchanged
import mlflow
mlflow.set_tracking_uri("https://mlflow.company.com")
mlflow.start_run()  # Authentication happens automatically
```

## Supported Providers

| Provider | Install Command | Authentication | Status |
|----------|----------------|----------------|---------|
| HashiCorp Vault | `pip install mlflow-secrets-auth[vault]` | Token, AppRole | ✅ Available |
| AWS Secrets Manager | `pip install mlflow-secrets-auth[aws]` | IAM, Access Keys | ✅ Available |
| Azure Key Vault | `pip install mlflow-secrets-auth[azure]` | Service Principal, Managed Identity | ✅ Available |
| Google Secret Manager | `pip install mlflow-secrets-auth[gcp]` | Service Account, Workload Identity | 🚧 Planned |

## Documentation

- **[Getting Started](https://hugodscarvalho.github.io/mlflow-secrets-auth/getting-started/)** - Quick setup guide
- **[Configuration](https://hugodscarvalho.github.io/mlflow-secrets-auth/configuration/)** - Complete configuration reference
- **[Providers](https://hugodscarvalho.github.io/mlflow-secrets-auth/providers/vault/)** - Provider-specific setup
- **[Troubleshooting](https://hugodscarvalho.github.io/mlflow-secrets-auth/troubleshooting/)** - Common issues and solutions

## Requirements

- Python 3.9+
- MLflow 2.20.4+
- Provider-specific SDKs (installed with extras)

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

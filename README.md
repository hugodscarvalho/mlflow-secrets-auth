# MLflow Secrets Auth

Secure authentication for MLflow with seamless secret manager integration.

[![CI](https://github.com/hugodscarvalho/mlflow-secrets-auth/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/hugodscarvalho/mlflow-secrets-auth/actions/workflows/ci-cd.yml)
[![Coverage](https://codecov.io/gh/hugodscarvalho/mlflow-secrets-auth/branch/main/graph/badge.svg)](https://codecov.io/gh/hugodscarvalho/mlflow-secrets-auth)
[![PyPI](https://img.shields.io/pypi/v/mlflow-secrets-auth.svg)](https://pypi.org/project/mlflow-secrets-auth/)
![Python](https://img.shields.io/pypi/pyversions/mlflow-secrets-auth.svg)
[![License](https://img.shields.io/github/license/hugodscarvalho/mlflow-secrets-auth.svg)](LICENSE)

---

## Why MLflow Secrets Auth?

`mlflow-secrets-auth` is a **pluggable authentication provider** for MLflow that removes the friction of managing credentials.  
It extends MLflow’s [tracking authentication system](https://mlflow.org/docs/latest/auth/index.html#pluggable-auth) by sourcing credentials from **enterprise-grade secret managers** and injecting them into every request — **without requiring changes to ML code**.

### Key Benefits

- **Zero Code Changes** – Drop-in plugin that works transparently with existing MLflow applications.  
- **Enterprise Security** – Native integration with HashiCorp Vault, AWS Secrets Manager, and Azure Key Vault.  
- **Production Ready** – Includes automatic token refresh, retries with jitter, secure in-memory caching, host allow-listing, and detailed logging.  
- **Developer Friendly** – Simple, environment-based configuration; no SDK boilerplate in training scripts.  

---

## Who is it for?

This plugin is designed for teams that:

- Run **MLflow Tracking Servers** behind reverse proxies (e.g., Nginx, API Gateway, corporate ingress) that expect **custom headers**.  
- Store and rotate credentials in **Vault, AWS Secrets Manager, or Azure Key Vault** instead of static environment variables.  
- Need to enforce **secure, centralized authentication** across multiple MLflow clients without modifying application code.  
- Want a **production-grade solution** that handles retries, caching, and secret rotation gracefully.  

---

## What does it add beyond MLflow’s built-in authentication?

MLflow already supports simple authentication via environment variables such as  
`MLFLOW_TRACKING_USERNAME`, `MLFLOW_TRACKING_PASSWORD`, and `MLFLOW_TRACKING_TOKEN`.  

However, these mechanisms assume **static, long-lived credentials**. In modern enterprise setups this is often not sufficient:  

- **Secrets rotate frequently** (short-lived Vault tokens, AWS STS creds).  
- **Multiple providers** must be supported across cloud and on-prem.  
- **Custom headers** are required when MLflow runs behind secured proxies or gateways.  

`mlflow-secrets-auth` fills these gaps by:  

- Pulling **fresh secrets on demand** from Vault, AWS, and Azure.  
- Handling **automatic refresh and retries** when tokens expire.  
- Supporting **customizable header names** beyond `Authorization`.  
- Providing a **unified interface** for multiple secret backends.  

The result is a **seamless, secure, and production-ready authentication layer** for MLflow.  

---

## Quick Start

Below are complete environment variable examples for each supported secrets provider.  
Set these before running MLflow, along with `MLFLOW_TRACKING_AUTH`.

### HashiCorp Vault

```bash
# Required
export VAULT_ADDR="https://vault.company.com"
export MLFLOW_VAULT_SECRET_PATH="secret/mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="vault"
export MLFLOW_TRACKING_AUTH="mlflow_secrets_auth"

# Authentication (choose one)
export VAULT_TOKEN="hvs.CAESIJL..."                    # Token auth
# OR
export VAULT_ROLE_ID="your-role-id"                    # AppRole auth
export VAULT_SECRET_ID="your-secret-id"

# Optional
export MLFLOW_VAULT_AUTH_MODE="bearer"                 # bearer|basic (default: bearer)
export MLFLOW_VAULT_TTL_SEC="300"                      # Cache TTL seconds (default: 300)
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"  # Host allow-list
```

### AWS Secrets Manager

```bash
# Required
export AWS_REGION="us-east-1"
export MLFLOW_AWS_SECRET_ID="prod/mlflow/auth"
export MLFLOW_SECRETS_AUTH_ENABLE="aws-secrets-manager"
export MLFLOW_TRACKING_AUTH="mlflow_secrets_auth"

# AWS Credentials (choose one method)
export AWS_ACCESS_KEY_ID="AKIA..."                     # Access key
export AWS_SECRET_ACCESS_KEY="..."
# OR use IAM roles, instance profiles, or other AWS auth methods

# Optional
export MLFLOW_AWS_AUTH_MODE="bearer"                   # bearer|basic (default: bearer)
export MLFLOW_AWS_TTL_SEC="300"                        # Cache TTL seconds (default: 300)
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"  # Host allow-list
```

### Azure Key Vault

```bash
# Required
export AZURE_KEY_VAULT_URL="https://myvault.vault.azure.net"
export MLFLOW_AZURE_SECRET_NAME="mlflow-auth-token"
export MLFLOW_SECRETS_AUTH_ENABLE="azure-key-vault"
export MLFLOW_TRACKING_AUTH="mlflow_secrets_auth"

# Azure Authentication (choose one method)
export AZURE_CLIENT_ID="..."                           # Service Principal
export AZURE_CLIENT_SECRET="..."
export AZURE_TENANT_ID="..."
# OR use Managed Identity, Azure CLI, or other Azure auth methods

# Optional
export MLFLOW_AZURE_AUTH_MODE="bearer"                 # bearer|basic (default: bearer)
export MLFLOW_AZURE_TTL_SEC="300"                      # Cache TTL seconds (default: 300)
export MLFLOW_SECRETS_ALLOWED_HOSTS="mlflow.company.com"  # Host allow-list
```

### Using MLflow (All Providers)

Once your environment variables are set, MLflow works exactly as before — no code changes needed:

```python
import mlflow

# Set your MLflow tracking server
mlflow.set_tracking_uri("https://mlflow.company.com")

# Use MLflow normally - authentication happens automatically
with mlflow.start_run():
    mlflow.log_param("alpha", 0.1)
    mlflow.log_metric("rmse", 0.89)
    mlflow.log_artifact("model.pkl")
    
print("✅ Authenticated and logged to MLflow successfully!")
```

---

## Live Demo

Experience the plugin in action with our complete working example:

```bash
git clone https://github.com/hugodscarvalho/mlflow-secrets-auth
cd mlflow-secrets-auth/examples/vault-nginx-mlflow
make demo
```

Once running, explore the **README.md** and **DEMO_OVERVIEW.md** files inside the `examples/vault-nginx-mlflow/` directory for setup details, architecture explanation, and usage instructions.

---

## Installation & Providers

| Provider              | Installation                              | Authentication Methods         | Status            |
|-----------------------|-------------------------------------------|--------------------------------|-------------------|
| **HashiCorp Vault**   | `pip install mlflow-secrets-auth[vault]`  | Token, AppRole                 | ✅ Available      |
| **AWS Secrets Manager** | `pip install mlflow-secrets-auth[aws]`  | IAM Roles, Access Keys         | ✅ Available      |
| **Azure Key Vault**   | `pip install mlflow-secrets-auth[azure]`  | Service Principal, Managed Identity | ✅ Available |
| **Google Secret Manager** | `pip install mlflow-secrets-auth[gcp]` | Service Account, Workload Identity | 🚧 Coming Soon |

---

## Documentation

📚 **Complete Documentation**: [hugodscarvalho.github.io/mlflow-secrets-auth](https://hugodscarvalho.github.io/mlflow-secrets-auth/)

- **[Getting Started](https://hugodscarvalho.github.io/mlflow-secrets-auth/getting-started/)** – Step-by-step setup guide  
- **[Configuration Reference](https://hugodscarvalho.github.io/mlflow-secrets-auth/configuration/)** – All configuration options  
- **[Provider Setup](https://hugodscarvalho.github.io/mlflow-secrets-auth/providers/vault/)** – Provider-specific configuration  
- **[Troubleshooting](https://hugodscarvalho.github.io/mlflow-secrets-auth/troubleshooting/)** – Common issues and solutions  

---

## System Requirements

- **Python**: 3.9 or higher  
- **MLflow**: 2.20.4 or higher  
- **Dependencies**: Provider-specific SDKs (automatically installed with extras)  

---

## License

Apache License 2.0 – see [LICENSE](LICENSE) file for details.

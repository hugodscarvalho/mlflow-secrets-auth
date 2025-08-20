# MLflow Secrets Auth - Demo Stack Overview

This demo stack provides a **complete, production-like example** of how `mlflow-secrets-auth` integrates with real-world infrastructure components. It's designed to be educational, showing the plugin's capabilities in a realistic multi-service environment.

## 🎯 What This Demo Proves

1. **Zero Code Changes**: Existing MLflow applications work transparently with the plugin
2. **Real Authentication**: Actual Basic Auth/API Key enforcement via Nginx
3. **Secret Management**: Credentials stored securely in HashiCorp Vault
4. **Production Patterns**: Reverse proxy, service discovery, health checks
5. **Easy Deployment**: One-command setup using Docker Compose

## 🏗️ Architecture Overview

```mermaid
graph TB
    Client[Python Client<br/>+ mlflow-secrets-auth] --> Nginx[Nginx Proxy<br/>Port 8080]
    Nginx --> MLflow[MLflow Server<br/>Port 5000]
    Client -.-> Vault[HashiCorp Vault<br/>Port 8200]
    
    subgraph "Authentication Flow"
        Vault --> |"1. Fetch credentials"| Client
        Client --> |"2. Inject headers"| Nginx
        Nginx --> |"3. Validate & forward"| MLflow
    end
    
    subgraph "Initialization"
        Setup[Vault Setup] --> |"Store credentials"| Vault
        AuthGen[htpasswd Generator] --> |"Create password file"| Nginx
    end
```

## 🔄 Authentication Flow

1. **Vault Setup**: `seed_vault.sh` stores MLflow credentials in Vault KV store
2. **Client Request**: Python client makes standard MLflow API calls
3. **Plugin Activation**: `mlflow-secrets-auth` intercepts the request
4. **Credential Fetch**: Plugin retrieves credentials from Vault
5. **Header Injection**: Plugin adds `Authorization` header automatically
6. **Nginx Validation**: Nginx validates credentials and forwards to MLflow
7. **MLflow Response**: Standard MLflow response returned to client

## 📁 File Structure

```
examples/vault-nginx-mlflow/
├── 🐳 docker-compose.yml        # Multi-service stack definition
├── 🔧 .env                      # Environment configuration
├── 🔧 .env.example              # Template for configuration
├── 🌐 nginx.conf                # Nginx reverse proxy config
├── 📖 README.md                 # Detailed documentation
├── ⚡ Makefile                  # Convenience commands
├── 📁 scripts/
│   ├── 🔐 seed_vault.sh         # Vault credential seeding
│   ├── 🔑 htpasswd_gen.sh       # Basic Auth password file
│   └── 🧪 test_setup.sh         # Setup validation
├── 📁 client/
│   ├── 🐍 demo.py               # Python demo script
│   ├── 📋 requirements.txt      # Python dependencies
│   └── 🐳 Dockerfile            # Client container build
└── 📁 auth/                     # Generated auth files
    └── 🔒 htpasswd              # Nginx password file
```

## 🎮 Demo Commands

| Command | Description |
|---------|-------------|
| `make demo` | **Complete demo** - setup, run, and show results |
| `make up` | Start all services in background |
| `make down` | Stop and remove all services |
| `make logs` | View logs from all services |
| `make test` | Validate setup before running |
| `make clean` | Remove everything (containers, volumes, files) |

## 🔐 Authentication Modes

### Basic Authentication (Default)
- **Vault Storage**: `{"username": "mlflow-user", "password": "secure-password-123"}`
- **Header Generated**: `Authorization: Basic bWxmbG93LXVzZXI6c2VjdXJlLXBhc3N3b3JkLTEyMw==`
- **Nginx Validation**: Against `/etc/nginx/htpasswd` file

### Bearer Token Authentication
- **Vault Storage**: `{"token": "mlflow-api-key-demo-567890abcdef"}`
- **Header Generated**: `Authorization: Bearer mlflow-api-key-demo-567890abcdef`
- **Nginx Validation**: Against hardcoded API key (demo only)

## 🌟 Key Features Demonstrated

### 🔧 Plugin Configuration
```bash
# Enable the plugin
MLFLOW_SECRETS_AUTH_ENABLE=vault

# Vault connection
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=demo-root-token-12345

# Secret location
MLFLOW_VAULT_SECRET_PATH=secret/mlflow/auth

# Authentication mode
MLFLOW_VAULT_AUTH_MODE=basic  # or "bearer"

# Security settings
MLFLOW_SECRETS_ALLOWED_HOSTS=nginx,nginx:80
```

### 🔒 Security Features
- **Host Allowlisting**: Plugin only activates for allowed hosts
- **Credential Masking**: Sensitive data redacted in logs
- **In-Memory Caching**: No credentials written to disk
- **TTL-Based Expiry**: Automatic cache invalidation

### 🚀 Production Readiness
- **Health Checks**: All services have proper health endpoints
- **Graceful Startup**: Services wait for dependencies
- **Logging**: Comprehensive logging with structured output
- **Error Handling**: Robust error handling and retries

## 🎓 Educational Value

This demo teaches:

1. **MLflow Plugin System**: How plugins integrate with MLflow's request lifecycle
2. **Secret Management**: Best practices for storing and retrieving credentials
3. **Reverse Proxy Patterns**: Using Nginx for authentication and routing
4. **Container Orchestration**: Multi-service coordination with Docker Compose
5. **Security Principles**: Defense in depth, least privilege, credential isolation

## 🔍 Verification Steps

The demo includes comprehensive verification:

1. **Plugin Loading**: Confirms the plugin is properly installed and detected
2. **Environment Check**: Validates all required configuration is present
3. **Vault Connectivity**: Tests connection and secret retrieval
4. **MLflow Readiness**: Waits for MLflow server to be healthy
5. **End-to-End Flow**: Runs actual experiments and verifies results

## 🌐 Access Points

After running the demo:

- **MLflow UI**: http://localhost:8080 (requires authentication)
- **Vault UI**: http://localhost:8200 (token: `demo-root-token-12345`)
- **Direct MLflow**: http://localhost:5000 (bypass auth - for testing)

## 💡 Extending the Demo

Ideas for customization:

1. **Different Auth Methods**: Try AppRole, JWT, or other Vault auth methods
2. **Multiple Environments**: Add staging/production configurations
3. **External Vault**: Connect to a real Vault instance
4. **TLS/SSL**: Add HTTPS termination at Nginx
5. **Monitoring**: Add Prometheus metrics and Grafana dashboards
6. **CI/CD Integration**: Use in automated testing pipelines

## 🏆 Production Migration

To adapt this for production:

1. **Vault**: Use proper Vault deployment with HA, TLS, and policies
2. **Authentication**: Implement proper RBAC and token lifecycle
3. **Networking**: Use service mesh or proper network policies
4. **Storage**: Use external databases and object storage
5. **Monitoring**: Add comprehensive observability
6. **Secrets**: Implement proper secret rotation and lifecycle

This demo provides a solid foundation for understanding and implementing `mlflow-secrets-auth` in real environments!

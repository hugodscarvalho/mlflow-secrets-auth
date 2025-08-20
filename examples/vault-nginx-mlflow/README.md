# MLflow Secrets Auth - Vault + Nginx + MLflow Demo

This demo stack demonstrates how `mlflow-secrets-auth` automatically injects authentication headers sourced from HashiCorp Vault to access an Nginx-protected MLflow Tracking Server.

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───▶│    Vault    │    │    Nginx    │───▶│   MLflow    │
│  (Python)   │    │ (Secrets)   │    │ (Auth Proxy)│    │  (Server)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       │                   │                   │                   │
    Requests           Fetches              Enforces          Serves
  MLflow API         credentials         authentication     experiments
     with              from KV              via Basic         and UI
  plugin enabled       store              Auth or API Key
```

## Components

- **Vault** (dev mode): Stores MLflow credentials in KV v2 store
- **Nginx**: Reverse proxy enforcing Basic Auth or API Key authentication
- **MLflow**: Standard MLflow tracking server with SQLite backend
- **Client**: Python container with the plugin installed, runs demo experiments

## Quick Start

1. **Setup environment**:
   ```bash
   cp .env.example .env
   # Edit .env if needed (defaults work for demo)
   # Ensure this is set for plugin activation:
   export MLFLOW_TRACKING_AUTH=mlflow_secrets_auth
   ```

2. **Run the demo**:
   ```bash
   make demo
   ```

3. **View results**:
   - MLflow UI: http://localhost:8080
   - Vault UI: http://localhost:8200 (token: `demo-root-token-12345`)

## Alternative Commands

```bash
# Build and start all services
make up

# Run just the client demo
make run-client

# View logs
make logs

# Stop and cleanup
make down
```

## Authentication Modes

The demo supports two authentication modes via the `AUTH_MODE` environment variable:

### Basic Authentication (default)
```bash
AUTH_MODE=basic
```
- Credentials stored in Vault as `{"username": "mlflow-user", "password": "secure-password-123"}`
- Plugin constructs `Authorization: Basic <base64(username:password)>`

### Bearer Token Authentication
```bash
AUTH_MODE=bearer
```
- API key stored in Vault as `{"token": "mlflow-api-key-demo-567890abcdef"}`
- Plugin constructs `Authorization: Bearer <token>`

## What the Demo Does

1. **Vault Setup**: Seeds Vault with MLflow credentials
2. **MLflow Server**: Starts vanilla MLflow server (no authentication built-in)
3. **Nginx Proxy**: Enforces authentication before forwarding to MLflow
4. **Plugin Demo**: Python client uses the plugin to:
   - Automatically fetch credentials from Vault
   - Inject appropriate `Authorization` headers
   - Log experiments to the protected MLflow server
   - Show that the plugin works transparently

## Demo Script Walkthrough

The `client/demo.py` script:

1. **Verifies plugin installation**: Checks that the plugin is properly loaded
2. **Tests connectivity**: Ensures Vault and MLflow are accessible
3. **Logs experiments**: Creates multiple MLflow runs with different parameters
4. **Validates results**: Confirms experiments were logged successfully

## Configuration

Key environment variables for the plugin:

| Variable | Description | Example |
|----------|-------------|---------|
| `MLFLOW_SECRETS_AUTH_ENABLE` | Enable the plugin | `vault` |
| `VAULT_ADDR` | Vault server address | `http://vault:8200` |
| `VAULT_TOKEN` | Vault authentication token | `demo-root-token-12345` |
| `MLFLOW_VAULT_SECRET_PATH` | Path to MLflow credentials | `secret/mlflow/auth` |
| `MLFLOW_VAULT_AUTH_MODE` | Authentication mode | `basic` or `bearer` |
| `MLFLOW_SECRETS_ALLOWED_HOSTS` | Host allowlist | `nginx,nginx:80` |

## Troubleshooting

### Plugin Not Working
```bash
# Check plugin is loaded
python -c "import mlflow_secrets_auth; print('Plugin loaded successfully')"

# Check MLflow recognizes the plugin
python -c "import mlflow; print(mlflow.utils.request_utils)"

# Make sure this is set (required for plugin activation):
echo $MLFLOW_TRACKING_AUTH  # Should output: mlflow_secrets_auth
```

### Vault Connection Issues
```bash
# Test Vault connectivity
curl -H "X-Vault-Token: demo-root-token-12345" \
     http://localhost:8200/v1/secret/data/mlflow/auth
```

### Authentication Issues
```bash
# Test Nginx directly with Basic Auth
curl -u "mlflow-user:secure-password-123" http://localhost:8080/api/2.0/mlflow/experiments/list

# Test with API Key
curl -H "Authorization: Bearer mlflow-api-key-demo-567890abcdef" \
     http://localhost:8080/api/2.0/mlflow/experiments/list
```

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs client
docker-compose logs nginx
docker-compose logs vault
```

## Production Considerations

This demo uses simplified configurations for learning purposes. For production:

1. **Vault**: Use proper authentication (not dev mode), enable TLS, use proper policies
2. **Nginx**: Use real SSL certificates, implement proper API key validation
3. **MLflow**: Use proper database backend (PostgreSQL), external artifact storage (S3)
4. **Security**: Implement proper secret rotation, network policies, monitoring

## Files

- `docker-compose.yml`: Multi-service stack definition
- `nginx.conf`: Nginx reverse proxy configuration
- `scripts/seed_vault.sh`: Vault initialization script
- `scripts/htpasswd_gen.sh`: Nginx password file generator
- `client/demo.py`: Python demo script
- `client/requirements.txt`: Python dependencies
- `Makefile`: Convenience commands

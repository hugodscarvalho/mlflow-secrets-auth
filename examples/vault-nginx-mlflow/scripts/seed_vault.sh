#!/bin/bash
set -e

echo "🔐 Seeding Vault with MLflow credentials..."

# Wait for Vault to be ready
echo "⏳ Waiting for Vault to be ready..."
for i in {1..30}; do
    if vault status >/dev/null 2>&1; then
        echo "✅ Vault is ready!"
        break
    fi
    echo "Waiting for Vault... ($i/30)"
    sleep 2
done

# Enable KV v2 secrets engine (if not already enabled)
echo "🔧 Enabling KV v2 secrets engine..."
vault secrets enable -version=2 -path=secret kv || echo "KV v2 already enabled"

# Determine credentials based on auth mode
if [ "$MLFLOW_VAULT_AUTH_MODE" = "bearer" ]; then
    echo "🔑 Storing API key for Bearer authentication..."
    vault kv put secret/mlflow/auth \
        token="$MLFLOW_API_KEY"
    echo "✅ API key stored in Vault at secret/mlflow/auth"
else
    echo "🔑 Storing username/password for Basic authentication..."
    vault kv put secret/mlflow/auth \
        username="$MLFLOW_USERNAME" \
        password="$MLFLOW_PASSWORD"
    echo "✅ Username/password stored in Vault at secret/mlflow/auth"
fi

# Verify the secret was stored
echo "🔍 Verifying stored credentials..."
vault kv get secret/mlflow/auth

echo "✅ Vault seeding completed successfully!"

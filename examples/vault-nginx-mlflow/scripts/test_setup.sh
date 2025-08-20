#!/bin/bash
set -e

echo "🧪 Testing demo stack components..."

# Test 1: Check if required files exist
echo "📁 Checking required files..."
required_files=(
    "docker-compose.yml"
    ".env"
    "nginx.conf"
    "scripts/seed_vault.sh"
    "scripts/htpasswd_gen.sh"
    "client/demo.py"
    "client/requirements.txt"
    "auth/htpasswd"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -eq 0 ]; then
    echo "✅ All required files present"
else
    echo "❌ Missing files: ${missing_files[*]}"
    exit 1
fi

# Test 2: Check Docker Compose configuration
echo "🐳 Validating Docker Compose configuration..."
if docker-compose config >/dev/null 2>&1; then
    echo "✅ Docker Compose configuration is valid"
else
    echo "❌ Docker Compose configuration is invalid"
    exit 1
fi

# Test 3: Check environment variables
echo "🔧 Checking environment configuration..."
source .env
required_env_vars=(
    "VAULT_ROOT_TOKEN"
    "VAULT_SECRET_PATH"
    "AUTH_MODE"
    "MLFLOW_USERNAME"
    "MLFLOW_PASSWORD"
)

missing_env_vars=()
for var in "${required_env_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_env_vars+=("$var")
    fi
done

if [ ${#missing_env_vars[@]} -eq 0 ]; then
    echo "✅ All required environment variables are set"
else
    echo "❌ Missing environment variables: ${missing_env_vars[*]}"
    exit 1
fi

echo ""
echo "🎉 Demo stack validation completed successfully!"
echo ""
echo "Ready to run the demo with:"
echo "  make demo      # Full demo (recommended)"
echo "  make up        # Start services only"
echo ""

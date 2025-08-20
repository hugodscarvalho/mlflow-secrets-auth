#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    source .env
fi

# Set defaults if not provided
MLFLOW_USERNAME=${MLFLOW_USERNAME:-mlflow-user}
MLFLOW_PASSWORD=${MLFLOW_PASSWORD:-secure-password-123}

echo "🔐 Generating htpasswd file for Nginx Basic Auth..."

# Create auth directory if it doesn't exist
mkdir -p auth

# Check if htpasswd command is available
if command -v htpasswd >/dev/null 2>&1; then
    # Use htpasswd if available
    htpasswd -bc auth/htpasswd "$MLFLOW_USERNAME" "$MLFLOW_PASSWORD"
    echo "✅ Generated auth/htpasswd using htpasswd command"
elif command -v python3 >/dev/null 2>&1; then
    # Fallback to Python if htpasswd is not available
    python3 -c "
import crypt
import sys

username = '$MLFLOW_USERNAME'
password = '$MLFLOW_PASSWORD'

# Generate bcrypt hash (most secure)
try:
    import bcrypt
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    print(f'{username}:{hashed}')
except ImportError:
    # Fallback to crypt (less secure but widely available)
    hashed = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    print(f'{username}:{hashed}')
" > auth/htpasswd
    echo "✅ Generated auth/htpasswd using Python"
else
    # Manual fallback - create a simple password file
    # Note: This is for demo purposes only, not secure for production
    echo "⚠️  Neither htpasswd nor Python available, creating simple password file"
    echo "$MLFLOW_USERNAME:$MLFLOW_PASSWORD" > auth/htpasswd
    echo "⚠️  Warning: Using plaintext passwords (demo only!)"
fi

echo "🔍 Created htpasswd file with user: $MLFLOW_USERNAME"
echo "📁 File saved at: auth/htpasswd"

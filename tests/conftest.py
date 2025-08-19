"""Test configuration and fixtures."""

import os
import pytest


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean up environment variables and cache before and after each test."""
    # Clear cache before test
    from mlflow_secrets_auth.cache import clear_cache
    clear_cache()

    # Store original values
    original_env = {}
    for key, value in os.environ.items():
        if key.startswith(('MLFLOW_', 'VAULT_', 'AWS_', 'AZURE_')):
            original_env[key] = value

    # Clear test-related environment variables
    for key in list(os.environ.keys()):
        if key.startswith(('MLFLOW_', 'VAULT_', 'AWS_', 'AZURE_')):
            del os.environ[key]

    yield

    # Clear cache after test
    clear_cache()

    # Restore original environment
    for key in list(os.environ.keys()):
        if key.startswith(('MLFLOW_', 'VAULT_', 'AWS_', 'AZURE_')):
            del os.environ[key]

    for key, value in original_env.items():
        os.environ[key] = value


@pytest.fixture
def vault_env():
    """Set up Vault environment variables for testing."""
    os.environ.update({
        "MLFLOW_SECRETS_AUTH_ENABLE": "vault",
        "VAULT_ADDR": "https://vault.example.com",
        "VAULT_TOKEN": "test-token",
        "MLFLOW_VAULT_SECRET_PATH": "secret/data/mlflow",
    })


@pytest.fixture
def aws_env():
    """Set up AWS environment variables for testing."""
    os.environ.update({
        "MLFLOW_SECRETS_AUTH_ENABLE": "aws-secrets-manager",
        "AWS_REGION": "us-west-2",
        "MLFLOW_AWS_SECRET_ID": "mlflow-auth-secret",
    })


@pytest.fixture
def azure_env():
    """Set up Azure environment variables for testing."""
    os.environ.update({
        "MLFLOW_SECRETS_AUTH_ENABLE": "azure-key-vault",
        "AZURE_KEY_VAULT_URL": "https://test-keyvault.vault.azure.net/",
        "MLFLOW_AZURE_SECRET_NAME": "mlflow-auth-secret",
    })

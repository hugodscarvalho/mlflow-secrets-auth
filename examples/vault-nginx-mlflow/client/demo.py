#!/usr/bin/env python3
"""MLflow Secrets Auth Demo Script.

This script demonstrates how the mlflow-secrets-auth plugin automatically
injects authentication headers sourced from HashiCorp Vault to access an
Nginx-protected MLflow Tracking Server.

The plugin works transparently—no code changes are needed!
"""

import os
import sys
import time
import logging

# IMPORTANT: MLflow will only use the secrets auth plugin if this env var is set.
# You can set it in your shell, .env, or here in code for demo purposes:
os.environ.setdefault("MLFLOW_TRACKING_AUTH", "mlflow_secrets_auth")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def check_plugin_installation():
    """Verify that the mlflow-secrets-auth plugin is properly installed."""
    logger.info("🔍 Checking plugin installation...")

    try:
        import mlflow_secrets_auth
        logger.info(f"✅ Plugin installed: version {mlflow_secrets_auth.__version__}")
        return True
    except ImportError as e:
        logger.error(f"❌ Plugin not installed: {e}")
        return False


def check_environment():
    """Verify that required environment variables are set."""
    logger.info("🔍 Checking environment configuration...")

    required_vars = [
        'MLFLOW_TRACKING_URI',
        'VAULT_ADDR',
        'VAULT_TOKEN',
        'MLFLOW_VAULT_SECRET_PATH',
        'MLFLOW_SECRETS_AUTH_ENABLE',
    ]

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Mask sensitive values in logs
            if 'TOKEN' in var or 'PASSWORD' in var:
                display_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            else:
                display_value = value
            logger.info(f"  {var}: {display_value}")

    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        return False

    logger.info("✅ Environment configuration looks good!")
    return True


def test_vault_connectivity():
    """Test connectivity to Vault."""
    logger.info("🔍 Testing Vault connectivity...")

    try:
        import hvac

        vault_addr = os.getenv('VAULT_ADDR')
        vault_token = os.getenv('VAULT_TOKEN')

        client = hvac.Client(url=vault_addr, token=vault_token)

        if not client.is_authenticated():
            logger.error("❌ Vault authentication failed")
            return False

        # Try to read the secret
        secret_path = os.getenv('MLFLOW_VAULT_SECRET_PATH', 'secret/mlflow/auth')
        try:
            # For KV v2, we need to read from the correct path
            if secret_path.startswith('secret/'):
                # Remove 'secret/' prefix for the API call
                kv_path = secret_path.replace('secret/', '')
            else:
                kv_path = secret_path
            client.secrets.kv.v2.read_secret_version(path=kv_path)
            logger.info("✅ Successfully connected to Vault and read secret")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Could not read secret (but connection works): {e}")
            return True  # Connection works even if secret read fails

    except ImportError:
        logger.error("❌ hvac package not available")
        return False
    except Exception as e:
        logger.error(f"❌ Vault connectivity test failed: {e}")
        return False


def wait_for_mlflow():
    """Wait for MLflow server to be ready."""
    logger.info("⏳ Waiting for MLflow server to be ready...")

    import requests

    tracking_uri = os.getenv('MLFLOW_TRACKING_URI')
    health_url = f"{tracking_uri}/health"

    for attempt in range(30):  # Wait up to 60 seconds
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                logger.info("✅ MLflow server is ready!")
                return True
        except Exception as e:
            logger.debug(f"MLflow not ready yet (attempt {attempt + 1}/30): {e}")

        time.sleep(2)

    logger.error("❌ MLflow server did not become ready in time")
    return False


def run_demo_experiments():
    """Run demo experiments to test plugin activation and error handling."""
    logger.info("🚀 Running demo experiments...")
    import mlflow
    import mlflow.sklearn
    from sklearn.datasets import load_wine
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score

    # Load demo dataset
    data = load_wine()
    x_train, x_test, y_train, y_test = train_test_split(
        data.data, data.target, test_size=0.2, random_state=42,
    )

    experiment_name = "vault-auth-demo"

    # --- Scenario 1: MLflow without plugin (should fail with 401) ---
    logger.info("\n❌ Scenario 1: MLflow without plugin (should fail)")
    # Temporarily unset the env var so plugin is not activated
    prev_auth = os.environ.pop("MLFLOW_TRACKING_AUTH", None)
    try:
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name="rf_model_fail"):
            model = RandomForestClassifier(n_estimators=10, max_depth=2, random_state=42)
            model.fit(x_train, y_train)
            y_pred = model.predict(x_test)
            accuracy = accuracy_score(y_test, y_pred)
            mlflow.log_metric("accuracy", accuracy)
        logger.error("❌ ERROR: MLflow run succeeded without authentication! This should not happen.")
        return False
    except Exception as e:
        logger.info(f"✅ Expected failure: {e}")
    finally:
        if prev_auth:
            os.environ["MLFLOW_TRACKING_AUTH"] = prev_auth

    # --- Scenario 2: MLflow with plugin (should succeed) ---
    logger.info("\n✅ Scenario 2: MLflow with plugin (should succeed)")
    try:
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name="rf_model_success"):
            model = RandomForestClassifier(n_estimators=10, max_depth=2, random_state=42)
            model.fit(x_train, y_train)
            y_pred = model.predict(x_test)
            accuracy = accuracy_score(y_test, y_pred)
            mlflow.log_metric("accuracy", accuracy)
        logger.info("✅ MLflow run succeeded with plugin authentication!")
        return True
    except Exception as e:
        logger.error(f"❌ MLflow run failed with plugin: {e}")
        return False


def verify_results():
    """Verify that experiments were logged successfully."""
    logger.info("🔍 Verifying experiment results...")

    try:
        import mlflow

        # List experiments
        experiments = mlflow.search_experiments()
        demo_exp = None
        for exp in experiments:
            if exp.name == "vault-auth-demo":
                demo_exp = exp
                break

        if not demo_exp:
            logger.error("❌ Demo experiment not found")
            return False

        # Search runs in the demo experiment
        runs = mlflow.search_runs(experiment_ids=[demo_exp.experiment_id])

        if runs.empty:
            logger.error("❌ No runs found in demo experiment")
            return False

        logger.info(f"✅ Found {len(runs)} runs in demo experiment")

        # Display summary
        logger.info("📊 Experiment Summary:")
        for idx, run in runs.iterrows():
            logger.info(f"  Run {idx + 1}: accuracy={run.get('metrics.accuracy', 'N/A'):.3f}, "
                       f"n_estimators={run.get('params.n_estimators', 'N/A')}")

        return True

    except Exception as e:
        logger.error(f"❌ Results verification failed: {e}")
        return False


def display_access_info():
    """Display information about accessing the demo results."""
    logger.info("🌐 Access Information:")
    logger.info("  MLflow UI: http://localhost:8080")
    logger.info("  Vault UI:  http://localhost:8200")
    logger.info("")
    logger.info("🔐 Demo Credentials:")

    auth_mode = os.getenv('MLFLOW_VAULT_AUTH_MODE', 'basic')
    if auth_mode == 'basic':
        username = os.getenv('MLFLOW_USERNAME', 'mlflow-user')
        password = os.getenv('MLFLOW_PASSWORD', 'secure-password-123')
        logger.info(f"  Username: {username}")
        logger.info(f"  Password: {password}")
    else:
        api_key = os.getenv('MLFLOW_API_KEY', 'mlflow-api-key-demo-567890abcdef')
        logger.info(f"  API Key: {api_key}")

    vault_token = os.getenv('VAULT_ROOT_TOKEN', 'demo-root-token-12345')
    logger.info(f"  Vault Token: {vault_token}")


def main():
    """Run the MLflow Secrets Auth demo."""
    logger.info("🚀 Starting MLflow Secrets Auth Demo")
    logger.info("=" * 50)

    # Pre-flight checks
    checks = [
        ("Plugin Installation", check_plugin_installation),
        ("Environment Configuration", check_environment),
        ("Vault Connectivity", test_vault_connectivity),
        ("MLflow Server Ready", wait_for_mlflow),
    ]

    for check_name, check_func in checks:
        logger.info(f"Running check: {check_name}")
        if not check_func():
            logger.error(f"❌ Check failed: {check_name}")
            sys.exit(1)
        logger.info("")

    # Run the actual demo
    logger.info("🎯 All checks passed! Running demo experiments...")
    logger.info("")

    if not run_demo_experiments():
        logger.error("❌ Demo experiments failed")
        sys.exit(1)

    logger.info("")
    if not verify_results():
        logger.error("❌ Results verification failed")
        sys.exit(1)

    logger.info("")
    logger.info("🎉 Demo completed successfully!")
    logger.info("=" * 50)
    display_access_info()
    logger.info("=" * 50)

    logger.info("💡 The plugin automatically handled authentication by:")
    logger.info("   1. Fetching credentials from Vault")
    logger.info("   2. Injecting Authorization headers")
    logger.info("   3. Allowing transparent MLflow API access")
    logger.info("")
    logger.info("✨ No code changes were needed - the plugin works transparently!")


if __name__ == "__main__":
    main()

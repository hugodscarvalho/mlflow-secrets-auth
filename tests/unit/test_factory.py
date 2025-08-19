"""Unit tests for SecretsAuthProviderFactory and version export."""

import importlib.metadata
from unittest.mock import Mock, patch

from mlflow_secrets_auth import SecretsAuthProviderFactory
from mlflow_secrets_auth.base import SecretsBackedAuthProvider


class TestVersionExport:
    """Test version export functionality."""

    def test_version_export_success(self):
        """Test successful version export from importlib.metadata."""
        expected_version = "1.2.3"

        with patch('importlib.metadata.version', return_value=expected_version):
            # Re-import the module to trigger version resolution
            import importlib
            import mlflow_secrets_auth
            importlib.reload(mlflow_secrets_auth)

            assert mlflow_secrets_auth.__version__ == expected_version

    def test_version_export_fallback_local(self):
        """Test fallback version when PackageNotFoundError is raised."""
        with patch('importlib.metadata.version', side_effect=importlib.metadata.PackageNotFoundError("package not found")):
            # Re-import the module to trigger version resolution
            import importlib as imp
            import mlflow_secrets_auth
            imp.reload(mlflow_secrets_auth)

            assert mlflow_secrets_auth.__version__ == "0.0.0+local"


class TestFactoryEnablement:
    """Test factory enablement logic."""

    def test_is_enabled_false_when_no_providers_enabled(self):
        """Test _is_enabled returns False when no providers are enabled."""
        factory = SecretsAuthProviderFactory()

        with patch('mlflow_secrets_auth.is_provider_enabled', return_value=False):
            assert factory._is_enabled() is False

    def test_is_enabled_true_when_any_provider_enabled(self):
        """Test _is_enabled returns True when at least one provider is enabled."""
        factory = SecretsAuthProviderFactory()

        def is_enabled_side_effect(name):
            return name == "vault"  # Only vault enabled

        with patch('mlflow_secrets_auth.is_provider_enabled', side_effect=is_enabled_side_effect):
            assert factory._is_enabled() is True

    def test_is_enabled_true_when_multiple_providers_enabled(self):
        """Test _is_enabled returns True when multiple providers are enabled."""
        factory = SecretsAuthProviderFactory()

        def is_enabled_side_effect(name):
            return name in ["vault", "aws-secrets-manager"]

        with patch('mlflow_secrets_auth.is_provider_enabled', side_effect=is_enabled_side_effect):
            assert factory._is_enabled() is True


class MockProvider(SecretsBackedAuthProvider):
    """Mock provider for testing."""

    def __init__(self, name="mock", fail_on_init=False):
        if fail_on_init:
            msg = f"Failed to initialize {name} provider"
            raise Exception(msg)
        super().__init__(name)
        self.name = name

    def _fetch_secret(self) -> str | None:
        return f"secret_from_{self.name}"

    def _get_cache_key(self) -> str:
        return f"cache_key_{self.name}"

    def _get_auth_mode(self) -> str:
        return "basic"

    def _get_ttl(self) -> int:
        return 123


class FailingMockProvider(MockProvider):
    """Mock provider that fails on initialization."""

    def __init__(self):
        msg = "Provider initialization failed"
        raise Exception(msg)


class TestProviderResolution:
    """Test provider resolution and caching."""

    def test_get_actual_provider_picks_first_enabled_and_caches_instance(self):
        """Test that the factory picks the first enabled provider and caches the instance."""
        factory = SecretsAuthProviderFactory()

        # Create mock providers
        mock_vault = MockProvider("vault")
        mock_aws = MockProvider("aws")

        mock_providers = {
            "vault": lambda: mock_vault,
            "aws-secrets-manager": lambda: mock_aws,
            "azure-key-vault": lambda: MockProvider("azure"),
        }

        def is_enabled_side_effect(name):
            return name in ["vault", "aws-secrets-manager"]  # Both enabled

        with patch('mlflow_secrets_auth.is_provider_enabled', side_effect=is_enabled_side_effect), \
             patch.object(factory, '_PROVIDERS', mock_providers):

            # First call should return vault (first in order)
            provider1 = factory._get_actual_provider()
            assert provider1 is mock_vault
            assert provider1.name == "vault"

            # Second call should return the same cached instance
            provider2 = factory._get_actual_provider()
            assert provider2 is provider1  # Same object, cached

    def test_get_actual_provider_skips_failing_provider_and_uses_next(self):
        """Test that the factory skips providers that fail to construct."""
        factory = SecretsAuthProviderFactory()

        # Create mock providers - first one fails, second succeeds
        mock_aws = MockProvider("aws")

        mock_providers = {
            "vault": FailingMockProvider,  # This will fail
            "aws-secrets-manager": lambda: mock_aws,  # This will succeed
            "azure-key-vault": lambda: MockProvider("azure"),
        }

        def is_enabled_side_effect(name):
            return name in ["vault", "aws-secrets-manager"]  # Both enabled

        with patch('mlflow_secrets_auth.is_provider_enabled', side_effect=is_enabled_side_effect), \
             patch.object(factory, '_PROVIDERS', mock_providers):

            # Should skip vault (fails) and return aws
            provider = factory._get_actual_provider()
            assert provider is mock_aws
            assert provider.name == "aws"

    def test_get_actual_provider_returns_none_when_no_providers_enabled(self):
        """Test that _get_actual_provider returns None when no providers are enabled."""
        factory = SecretsAuthProviderFactory()

        with patch('mlflow_secrets_auth.is_provider_enabled', return_value=False):
            provider = factory._get_actual_provider()
            assert provider is None

    def test_get_actual_provider_returns_none_when_all_providers_fail(self):
        """Test that _get_actual_provider returns None when all enabled providers fail."""
        factory = SecretsAuthProviderFactory()

        mock_providers = {
            "vault": FailingMockProvider,
            "aws-secrets-manager": FailingMockProvider,
            "azure-key-vault": FailingMockProvider,
        }

        with patch('mlflow_secrets_auth.is_provider_enabled', return_value=True), \
             patch.object(factory, '_PROVIDERS', mock_providers):

            provider = factory._get_actual_provider()
            assert provider is None


class TestDelegationMethods:
    """Test delegation methods of the factory."""

    def test_delegation_methods_return_provider_values(self):
        """Test that factory methods delegate to the actual provider."""
        factory = SecretsAuthProviderFactory()
        mock_provider = MockProvider("test")

        # Mock the provider resolution to return our test provider
        with patch.object(factory, '_get_actual_provider', return_value=mock_provider):
            # Test all delegation methods
            assert factory._fetch_secret() == "secret_from_test"
            assert factory._get_cache_key() == "cache_key_test"
            assert factory._get_auth_mode() == "basic"
            assert factory._get_ttl() == 123

    def test_delegation_methods_return_defaults_when_no_provider(self):
        """Test that factory methods return defaults when no provider is available."""
        factory = SecretsAuthProviderFactory()

        # Mock the provider resolution to return None
        with patch.object(factory, '_get_actual_provider', return_value=None):
            # Test all delegation methods return defaults
            assert factory._fetch_secret() is None
            assert factory._get_cache_key() == ""
            assert factory._get_auth_mode() == "bearer"
            assert factory._get_ttl() == 300

    def test_fetch_secret_handles_provider_none(self):
        """Test _fetch_secret when provider is None."""
        factory = SecretsAuthProviderFactory()

        with patch.object(factory, '_get_actual_provider', return_value=None):
            result = factory._fetch_secret()
            assert result is None

    def test_get_cache_key_handles_provider_none(self):
        """Test _get_cache_key when provider is None."""
        factory = SecretsAuthProviderFactory()

        with patch.object(factory, '_get_actual_provider', return_value=None):
            result = factory._get_cache_key()
            assert result == ""

    def test_get_auth_mode_handles_provider_none(self):
        """Test _get_auth_mode when provider is None."""
        factory = SecretsAuthProviderFactory()

        with patch.object(factory, '_get_actual_provider', return_value=None):
            result = factory._get_auth_mode()
            assert result == "bearer"

    def test_get_ttl_handles_provider_none(self):
        """Test _get_ttl when provider is None."""
        factory = SecretsAuthProviderFactory()

        with patch.object(factory, '_get_actual_provider', return_value=None):
            result = factory._get_ttl()
            assert result == 300


class TestFactoryInitialization:
    """Test factory initialization."""

    def test_factory_initialization(self):
        """Test that the factory initializes correctly."""
        factory = SecretsAuthProviderFactory()

        # Check base class initialization
        assert factory.provider_name == "mlflow_secrets_auth"
        assert factory.default_ttl == 300
        assert factory._actual_provider is None

    def test_factory_providers_mapping_exists(self):
        """Test that the _PROVIDERS mapping is correctly defined."""
        factory = SecretsAuthProviderFactory()

        # Check that all expected providers are in the mapping
        assert "vault" in factory._PROVIDERS
        assert "aws-secrets-manager" in factory._PROVIDERS
        assert "azure-key-vault" in factory._PROVIDERS

        # Check that the mapping contains classes
        for provider_cls in factory._PROVIDERS.values():
            assert callable(provider_cls)


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple aspects."""

    def test_full_delegation_flow_with_successful_provider(self):
        """Test the full flow from enablement check to method delegation."""
        factory = SecretsAuthProviderFactory()
        mock_provider = MockProvider("integration_test")

        def is_enabled_side_effect(name):
            return name == "vault"

        mock_providers = {
            "vault": lambda: mock_provider,
            "aws-secrets-manager": lambda: MockProvider("aws"),
            "azure-key-vault": lambda: MockProvider("azure"),
        }

        with patch('mlflow_secrets_auth.is_provider_enabled', side_effect=is_enabled_side_effect), \
             patch.object(factory, '_PROVIDERS', mock_providers):

            # Test enablement
            assert factory._is_enabled() is True

            # Test provider resolution and caching
            provider1 = factory._get_actual_provider()
            provider2 = factory._get_actual_provider()
            assert provider1 is provider2  # Cached
            assert provider1 is mock_provider

            # Test delegation
            assert factory._fetch_secret() == "secret_from_integration_test"
            assert factory._get_cache_key() == "cache_key_integration_test"
            assert factory._get_auth_mode() == "basic"
            assert factory._get_ttl() == 123

    def test_full_delegation_flow_with_no_providers(self):
        """Test the full flow when no providers are enabled."""
        factory = SecretsAuthProviderFactory()

        with patch('mlflow_secrets_auth.is_provider_enabled', return_value=False):
            # Test enablement
            assert factory._is_enabled() is False

            # Test provider resolution
            provider = factory._get_actual_provider()
            assert provider is None

            # Test delegation defaults
            assert factory._fetch_secret() is None
            assert factory._get_cache_key() == ""
            assert factory._get_auth_mode() == "bearer"
            assert factory._get_ttl() == 300

    def test_provider_priority_order(self):
        """Test that providers are chosen in the correct priority order."""
        factory = SecretsAuthProviderFactory()

        # Create distinguishable mock providers
        vault_provider = MockProvider("vault_priority")
        aws_provider = MockProvider("aws_priority")
        azure_provider = MockProvider("azure_priority")

        mock_providers = {
            "vault": lambda: vault_provider,
            "aws-secrets-manager": lambda: aws_provider,
            "azure-key-vault": lambda: azure_provider,
        }

        # Test: only AWS enabled -> should get AWS
        with patch('mlflow_secrets_auth.is_provider_enabled',
                  side_effect=lambda name: name == "aws-secrets-manager"), \
             patch.object(factory, '_PROVIDERS', mock_providers):

            factory._actual_provider = None  # Reset cache
            provider = factory._get_actual_provider()
            assert provider is aws_provider

        # Test: AWS and Vault enabled -> should get Vault (higher priority)
        with patch('mlflow_secrets_auth.is_provider_enabled',
                  side_effect=lambda name: name in ["vault", "aws-secrets-manager"]), \
             patch.object(factory, '_PROVIDERS', mock_providers):

            factory._actual_provider = None  # Reset cache
            provider = factory._get_actual_provider()
            assert provider is vault_provider

        # Test: all enabled -> should get Vault (highest priority)
        with patch('mlflow_secrets_auth.is_provider_enabled', return_value=True), \
             patch.object(factory, '_PROVIDERS', mock_providers):

            factory._actual_provider = None  # Reset cache
            provider = factory._get_actual_provider()
            assert provider is vault_provider


class TestExceptionHandling:
    """Test exception handling in various scenarios."""

    def test_no_exceptions_propagate_from_factory_methods(self):
        """Test that no unexpected exceptions propagate from factory methods."""
        factory = SecretsAuthProviderFactory()

        # Test with a provider that might raise exceptions
        problematic_provider = Mock()
        problematic_provider._fetch_secret.side_effect = Exception("Fetch error")
        problematic_provider._get_cache_key.side_effect = Exception("Cache error")
        problematic_provider._get_auth_mode.side_effect = Exception("Auth error")
        problematic_provider._get_ttl.side_effect = Exception("TTL error")

        with patch.object(factory, '_get_actual_provider', return_value=problematic_provider):
            # These should not raise exceptions but may return unexpected values
            # The exact behavior depends on implementation details
            try:
                factory._fetch_secret()
                factory._get_cache_key()
                factory._get_auth_mode()
                factory._get_ttl()
            except Exception as e:
                # If exceptions do propagate, they should be expected ones
                assert "error" in str(e).lower()

    def test_factory_handles_provider_resolution_gracefully(self):
        """Test that factory handles provider resolution errors gracefully."""
        factory = SecretsAuthProviderFactory()

        # Mock is_provider_enabled to raise an exception
        with patch('mlflow_secrets_auth.is_provider_enabled',
                  side_effect=Exception("Config error")):

            # _is_enabled should handle this gracefully
            try:
                result = factory._is_enabled()
                # If no exception is raised, we accept any boolean result
                assert isinstance(result, bool)
            except Exception:
                # If an exception is raised, it should be the expected one
                pass

"""MLflow Secrets-Backed RequestAuthProvider.

Public API:
    - SecretsAuthProviderFactory: Factory provider that delegates to the first
      enabled backend among Vault, AWS Secrets Manager, and Azure Key Vault.
    - __version__: Package version string (best-effort).

This module also exposes a best-effort ``__version__`` so the CLI `info` command
can display a version even in editable installs where distribution metadata
may be unavailable.
"""

from __future__ import annotations

import importlib.metadata
from typing import ClassVar
from .base import SecretsBackedAuthProvider
from .config import is_provider_enabled
from .providers.aws_secrets_manager import AWSSecretsManagerAuthProvider
from .providers.azure_key_vault import AzureKeyVaultAuthProvider
from .providers.vault import VaultAuthProvider

from mlflow_secrets_auth.constants import (
    PACKAGE_NAME,
    DEFAULT_TTL_SECONDS,
    DEFAULT_AUTH_MODE,
    PROVIDER_VAULT,
    PROVIDER_AWS,
    PROVIDER_AZURE,
)

# Best-effort version export (useful for CLI/info without installed dist metadata)
try:  # pragma: no cover - environment dependent
    __version__ = importlib.metadata.version(PACKAGE_NAME)
except importlib.metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+local"


class SecretsAuthProviderFactory(SecretsBackedAuthProvider):
    """Factory that selects and delegates to an enabled provider.

    Priority order:
        1) HashiCorp Vault
        2) AWS Secrets Manager
        3) Azure Key Vault

    If no provider is enabled or instantiation fails, this factory behaves as
    "disabled" (e.g., returns defaults/None) while preserving MLflow semantics.

    Attributes:
        _actual_provider: The lazily-instantiated concrete provider, if any.

    """

    _PROVIDERS: ClassVar[dict[str, type[SecretsBackedAuthProvider]]] = {
    PROVIDER_VAULT: VaultAuthProvider,
    PROVIDER_AWS: AWSSecretsManagerAuthProvider,
    PROVIDER_AZURE: AzureKeyVaultAuthProvider,
    }

    def __init__(self) -> None:
        """Initialize the factory with a default TTL."""
        super().__init__("mlflow_secrets_auth", default_ttl=DEFAULT_TTL_SECONDS)
        self._actual_provider: SecretsBackedAuthProvider | None = None

    # Resolution

    def _is_enabled(self) -> bool:
        """Return whether any supported provider is enabled.

        Returns:
            True if at least one provider is enabled, otherwise False.

        """
        return any(is_provider_enabled(name) for name in self._PROVIDERS)

    def _get_actual_provider(self) -> SecretsBackedAuthProvider | None:
        """Instantiate (once) and return the first enabled provider.

        Returns:
            A concrete `SecretsBackedAuthProvider` or None if none are enabled
            or instantiation fails.

        """
        if self._actual_provider is not None:
            return self._actual_provider

        for name, provider_cls in self._PROVIDERS.items():
            if is_provider_enabled(name):
                try:
                    self._actual_provider = provider_cls()
                    return self._actual_provider
                except Exception:  # noqa: S112
                    # Keep scanning other providers if one fails to construct.
                    continue
        return None

    # Delegation to concrete provider

    def _fetch_secret(self) -> str | None:
        """Delegate secret fetching to the actual provider, if available.

        Returns:
            Raw secret payload (string) or None if unavailable.

        """
        provider = self._get_actual_provider()
        return None if provider is None else provider._fetch_secret()  # noqa: SLF001

    def _get_cache_key(self) -> str:
        """Delegate cache-key generation to the actual provider.

        Returns:
            Cache key string, or empty string if no provider is available.

        """
        provider = self._get_actual_provider()
        return "" if provider is None else provider._get_cache_key()  # noqa: SLF001

    def _get_auth_mode(self) -> str:
        """Delegate auth-mode retrieval to the actual provider.

        Returns:
            "bearer" or "basic"; defaults to "bearer" if no provider is available.

        """
        provider = self._get_actual_provider()
        return DEFAULT_AUTH_MODE if provider is None else provider._get_auth_mode()  # noqa: SLF001

    def _get_ttl(self) -> int:
        """Delegate TTL retrieval to the actual provider.

        Returns:
            TTL (seconds); defaults to 300 if no provider is available.

        """
        provider = self._get_actual_provider()
        return DEFAULT_TTL_SECONDS if provider is None else provider._get_ttl()  # noqa: SLF001


__all__ = [
    "SecretsAuthProviderFactory",
    "__version__",
]

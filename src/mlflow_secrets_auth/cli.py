"""Command-line interface (CLI) for MLflow Secrets Auth.

Subcommands:
  * info   – Show version, enabled providers, and configuration snapshot.
  * doctor – Run diagnostics against the configured provider.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import sys
from typing import Protocol, runtime_checkable
from urllib.parse import urlparse

import requests

from .cache import get_cache_size
from .config import get_allowed_hosts, get_auth_header_name, is_provider_enabled
from .providers.aws_secrets_manager import AWSSecretsManagerAuthProvider
from .providers.azure_key_vault import AzureKeyVaultAuthProvider
from .providers.vault import VaultAuthProvider
from .utils import setup_logger
import contextlib


@runtime_checkable
class _DiagProvider(Protocol):
    """Minimal protocol for providers used by diagnostics."""

    def _get_auth_mode(self) -> str: ...
    def _get_ttl(self) -> int: ...
    def _fetch_secret_cached(self) -> dict[str, str] | None: ...
    def _create_auth(self, secret: dict[str, str]) -> requests.auth.AuthBase: ...
    def get_request_auth(self, url: str) -> requests.auth.AuthBase | None: ...


ProviderTuple = tuple[str | None, _DiagProvider | None]

PROVIDERS: dict[str, type[_DiagProvider]] = {
    "vault": VaultAuthProvider,
    "aws-secrets-manager": AWSSecretsManagerAuthProvider,
    "azure-key-vault": AzureKeyVaultAuthProvider,
}


def get_enabled_provider() -> ProviderTuple:
    """Return the first enabled provider as (name, instance), or (None, None).

    Returns:
        Tuple of provider name and instance, or (None, None) if none enabled.

    """
    for name, cls in PROVIDERS.items():
        if is_provider_enabled(name):
            try:
                return name, cls()  # type: ignore[call-arg]  # compatible ctor
            except Exception:  # pragma: no cover — defensive
                return name, None
    return None, None


def _print_header(title: str) -> None:
    """Print a decorated section header.

    Args:
        title: Section title.

    """


def info_command(_: argparse.Namespace) -> int:
    """Show plugin version and configuration snapshot.

    Returns:
        Process exit code (0 on success, non-zero on error).

    """
    setup_logger("mlflow_secrets_auth.cli")

    _print_header("MLflow Secrets Auth – Info")

    # Version
    try:
        importlib.metadata.version("mlflow-secrets-auth")
    except importlib.metadata.PackageNotFoundError:
        # Fallback for editable installs if distribution metadata is absent
        try:
            pass  # type: ignore
        except Exception:
            pass

    # Providers
    [name for name in PROVIDERS if is_provider_enabled(name)]

    # Config snapshot
    get_allowed_hosts()
    return 0


def doctor_command(args: argparse.Namespace) -> int:
    """Run diagnostics against the configured provider.

    Steps:
      1) Resolve enabled provider.
      2) Validate provider configuration (auth mode, TTL, header).
      3) Fetch secret and construct an auth object.
      4) Optional dry-run: issue a HEAD request to the given URL's origin.

    Args:
        args: Parsed CLI args (supports `--dry-run` URL).

    Returns:
        Process exit code (0 on success, non-zero on error).

    """
    setup_logger("mlflow_secrets_auth.cli")

    _print_header("MLflow Secrets Auth – Doctor")

    provider_name, provider = get_enabled_provider()
    if provider_name is None or provider is None:
        return 1

    # Config snapshot
    try:
        _ = provider._get_auth_mode()
        _ = get_auth_header_name()
        _ = provider._get_ttl()
        _ = get_cache_size()
        allowed_hosts = get_allowed_hosts()
    except Exception:  # pragma: no cover
        return 1

    # Test secret fetch + auth construction
    try:
        secret_data = provider._fetch_secret_cached()
        if not secret_data:
            return 1

        try:
            provider._create_auth(secret_data)
        except Exception:
            return 1
    except Exception:  # pragma: no cover
        return 1

    # Optional dry-run against a URL
    if args.dry_run:
        parsed = urlparse(args.dry_run)
        if not parsed.scheme or not parsed.netloc:
            return 1

        if allowed_hosts and parsed.hostname not in allowed_hosts:
            return 1

        try:
            auth = provider.get_request_auth(args.dry_run)
            if auth is None:
                return 1

            origin = f"{parsed.scheme}://{parsed.netloc}/"
            with contextlib.suppress(requests.exceptions.RequestException):
                requests.head(origin, auth=auth, timeout=10, allow_redirects=True)
        except Exception:  # pragma: no cover
            return 1

    return 0


def main() -> int:
    """Main CLI entry point.

    Returns:
        Process exit code (0 on success, non-zero on error).

    """
    parser = argparse.ArgumentParser(description="MLflow Secrets Auth CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Run diagnostics")
    doctor_parser.add_argument(
        "--dry-run",
        metavar="URL",
        help="Test auth against specified MLflow tracking URL",
    )

    # info
    subparsers.add_parser("info", help="Show plugin information and configuration")

    args = parser.parse_args()

    if args.command == "doctor":
        return doctor_command(args)
    if args.command == "info":
        return info_command(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

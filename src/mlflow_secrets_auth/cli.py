"""Command-line interface (CLI) for MLflow Secrets Auth.

Subcommands:
  * info   - Show version, enabled providers, and configuration snapshot.
  * doctor - Run diagnostics against the configured provider.
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
from .constants import (
    CLI_COMMAND_DOCTOR,
    CLI_COMMAND_INFO,
    CLI_ARG_DRY_RUN,
    DEFAULT_REQUEST_TIMEOUT,
    EXIT_SUCCESS,
    EXIT_ERROR,
    PACKAGE_NAME,
    PROVIDER_AWS,
    PROVIDER_AZURE,
    PROVIDER_VAULT,
)
from .messages import (
    CLI_DESCRIPTION,
    CLI_HEADER_DOCTOR,
    CLI_HEADER_INFO,
    CLI_HELP_COMMANDS,
    CLI_HELP_DOCTOR,
    CLI_HELP_DRY_RUN,
    CLI_HELP_INFO,
    INFO_VERSION,
    INFO_VERSION_DEV,
    INFO_ENABLED_PROVIDERS,
    INFO_NO_ENABLED_PROVIDERS,
    INFO_DISABLED_PROVIDERS,
    INFO_ALLOWED_HOSTS,
    INFO_ALL_HOSTS_ALLOWED,
    INFO_AUTH_HEADER,
    INFO_CACHE_SIZE,
    DOCTOR_NO_PROVIDERS_ENABLED,
    DOCTOR_AVAILABLE_PROVIDERS,
    DOCTOR_FOUND_ENABLED,
    DOCTOR_INIT_FAILED,
    DOCTOR_PROVIDER_OK,
    DOCTOR_AUTH_MODE_OK,
    DOCTOR_AUTH_HEADER_OK,
    DOCTOR_TTL_OK,
    DOCTOR_CACHE_SIZE_OK,
    DOCTOR_ALLOWED_HOSTS_OK,
    DOCTOR_ALL_HOSTS_OK,
    DOCTOR_CONFIG_ERROR,
    DOCTOR_TESTING_SECRET_FETCH,
    DOCTOR_SECRET_FETCH_FAILED,
    DOCTOR_SECRET_FETCH_OK,
    DOCTOR_TESTING_AUTH_CONSTRUCTION,
    DOCTOR_AUTH_CONSTRUCTION_OK,
    DOCTOR_AUTH_TYPE,
    DOCTOR_AUTH_CONSTRUCTION_FAILED,
    DOCTOR_SECRET_FETCH_ERROR,
    DOCTOR_DRY_RUN_TESTING,
    DOCTOR_INVALID_URL,
    DOCTOR_HOST_NOT_ALLOWED,
    DOCTOR_NO_AUTH_FOR_URL,
    DOCTOR_MAKING_REQUEST,
    DOCTOR_REQUEST_SUCCESS,
    DOCTOR_REQUEST_FAILED,
    DOCTOR_DRY_RUN_FAILED,
    DOCTOR_ALL_PASSED,
    STATUS_SUCCESS,
    STATUS_ERROR,
    STATUS_TESTING,
)
from .providers.aws_secrets_manager import AWSSecretsManagerAuthProvider
from .providers.azure_key_vault import AzureKeyVaultAuthProvider
from .providers.vault import VaultAuthProvider
from .utils import setup_logger, is_host_allowed
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
    PROVIDER_VAULT: VaultAuthProvider,
    PROVIDER_AWS: AWSSecretsManagerAuthProvider,
    PROVIDER_AZURE: AzureKeyVaultAuthProvider,
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
    print(f"\n{title}")
    print("=" * len(title))


def info_command(_: argparse.Namespace) -> int:
    """Show plugin version and configuration snapshot.

    Returns:
        Process exit code (0 on success, non-zero on error).

    """
    setup_logger("mlflow_secrets_auth.cli")

    _print_header(CLI_HEADER_INFO)

    # Version
    try:
        version = importlib.metadata.version(PACKAGE_NAME)
        print(f"{STATUS_SUCCESS} {INFO_VERSION.format(version=version)}")
    except importlib.metadata.PackageNotFoundError:
        # Fallback for editable installs if distribution metadata is absent
        with contextlib.suppress(Exception):
            print(f"{STATUS_SUCCESS} {INFO_VERSION_DEV}")

    # Providers
    enabled_providers = [name for name in PROVIDERS if is_provider_enabled(name)]
    if enabled_providers:
        print(f"{STATUS_SUCCESS} {INFO_ENABLED_PROVIDERS.format(providers=', '.join(enabled_providers))}")
    else:
        print(f"{STATUS_ERROR} {INFO_NO_ENABLED_PROVIDERS}")

    all_providers = list(PROVIDERS.keys())
    disabled_providers = [name for name in all_providers if name not in enabled_providers]
    if disabled_providers:
        print(f"  {INFO_DISABLED_PROVIDERS.format(providers=', '.join(disabled_providers))}")

    # Config snapshot
    allowed_hosts = get_allowed_hosts()
    if allowed_hosts:
        print(f"{STATUS_SUCCESS} {INFO_ALLOWED_HOSTS.format(hosts=', '.join(allowed_hosts))}")
    else:
        print(f"{STATUS_SUCCESS} {INFO_ALL_HOSTS_ALLOWED}")

    auth_header = get_auth_header_name()
    print(f"{STATUS_SUCCESS} {INFO_AUTH_HEADER.format(header=auth_header)}")

    cache_size = get_cache_size()
    print(f"{STATUS_SUCCESS} {INFO_CACHE_SIZE.format(size=cache_size)}")

    return EXIT_SUCCESS


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

    _print_header(CLI_HEADER_DOCTOR)

    provider_name, provider = get_enabled_provider()
    if provider_name is None or provider is None:
        enabled_providers = [name for name in PROVIDERS if is_provider_enabled(name)]
        if not enabled_providers:
            print(f"{STATUS_ERROR} {DOCTOR_NO_PROVIDERS_ENABLED}")
            print(f"  {DOCTOR_AVAILABLE_PROVIDERS.format(providers=', '.join(PROVIDERS.keys()))}")
        else:
            print(f"{STATUS_ERROR} {DOCTOR_FOUND_ENABLED.format(providers=', '.join(enabled_providers))}")
            print(f"  {DOCTOR_INIT_FAILED}")
        return EXIT_ERROR

    print(f"{STATUS_SUCCESS} {DOCTOR_PROVIDER_OK.format(provider=provider_name)}")

    # Config snapshot
    try:
        auth_mode = provider._get_auth_mode()  # noqa: SLF001
        print(f"{STATUS_SUCCESS} {DOCTOR_AUTH_MODE_OK.format(mode=auth_mode)}")

        auth_header = get_auth_header_name()
        print(f"{STATUS_SUCCESS} {DOCTOR_AUTH_HEADER_OK.format(header=auth_header)}")

        ttl = provider._get_ttl()  # noqa: SLF001
        print(f"{STATUS_SUCCESS} {DOCTOR_TTL_OK.format(ttl=ttl)}")

        cache_size = get_cache_size()
        print(f"{STATUS_SUCCESS} {DOCTOR_CACHE_SIZE_OK.format(size=cache_size)}")

        allowed_hosts = get_allowed_hosts()
        if allowed_hosts:
            print(f"{STATUS_SUCCESS} {DOCTOR_ALLOWED_HOSTS_OK.format(hosts=', '.join(allowed_hosts))}")
        else:
            print(f"{STATUS_SUCCESS} {DOCTOR_ALL_HOSTS_OK}")
    except Exception as e:
        print(f"{STATUS_ERROR} {DOCTOR_CONFIG_ERROR.format(error=str(e))}")
        return EXIT_ERROR

    # Test secret fetch + auth construction
    try:
        print(f"{STATUS_TESTING} {DOCTOR_TESTING_SECRET_FETCH}")
        secret_data = provider._fetch_secret_cached()  # noqa: SLF001
        if not secret_data:
            print(f"{STATUS_ERROR} {DOCTOR_SECRET_FETCH_FAILED}")
            return EXIT_ERROR

        print(f"{STATUS_SUCCESS} {DOCTOR_SECRET_FETCH_OK}")

        try:
            print(f"{STATUS_TESTING} {DOCTOR_TESTING_AUTH_CONSTRUCTION}")
            auth = provider._create_auth(secret_data)  # noqa: SLF001
            print(f"{STATUS_SUCCESS} {DOCTOR_AUTH_CONSTRUCTION_OK}")
            print(f"  {DOCTOR_AUTH_TYPE.format(auth_type=type(auth).__name__)}")
        except Exception as e:
            print(f"{STATUS_ERROR} {DOCTOR_AUTH_CONSTRUCTION_FAILED.format(error=str(e))}")
            return EXIT_ERROR
    except Exception as e:
        print(f"{STATUS_ERROR} {DOCTOR_SECRET_FETCH_ERROR.format(error=str(e))}")
        return EXIT_ERROR

    # Optional dry-run against a URL
    if args.dry_run:
        print(f"{STATUS_TESTING} {DOCTOR_DRY_RUN_TESTING.format(url=args.dry_run)}")

        parsed = urlparse(args.dry_run)
        if not parsed.scheme or not parsed.netloc:
            print(f"{STATUS_ERROR} {DOCTOR_INVALID_URL}")
            return EXIT_ERROR

        allowed_hosts = get_allowed_hosts()
        if allowed_hosts and not is_host_allowed(args.dry_run, allowed_hosts):
            print(f"{STATUS_ERROR} {DOCTOR_HOST_NOT_ALLOWED.format(host=parsed.netloc, allowed_hosts=', '.join(allowed_hosts))}")
            return EXIT_ERROR

        try:
            auth = provider.get_request_auth(args.dry_run)
            if auth is None:
                print(f"{STATUS_ERROR} {DOCTOR_NO_AUTH_FOR_URL}")
                return EXIT_ERROR

            origin = f"{parsed.scheme}://{parsed.netloc}/"
            print(f"{STATUS_TESTING} {DOCTOR_MAKING_REQUEST.format(origin=origin)}")

            try:
                response = requests.head(origin, auth=auth, timeout=DEFAULT_REQUEST_TIMEOUT, allow_redirects=True)
                print(f"{STATUS_SUCCESS} {DOCTOR_REQUEST_SUCCESS.format(status_code=response.status_code)}")
            except requests.exceptions.RequestException as e:
                print(f"{STATUS_ERROR} {DOCTOR_REQUEST_FAILED.format(error=str(e))}")
                # Don't return error code for network issues in dry-run

        except Exception as e:
            print(f"{STATUS_ERROR} {DOCTOR_DRY_RUN_FAILED.format(error=str(e))}")
            return EXIT_ERROR

    print(f"\n{STATUS_SUCCESS} {DOCTOR_ALL_PASSED}")
    return EXIT_SUCCESS


def main() -> int:
    """Run the CLI entry point.

    Returns:
        Process exit code (0 on success, non-zero on error).

    """
    parser = argparse.ArgumentParser(description=CLI_DESCRIPTION)
    subparsers = parser.add_subparsers(dest="command", help=CLI_HELP_COMMANDS)

    # doctor
    doctor_parser = subparsers.add_parser(CLI_COMMAND_DOCTOR, help=CLI_HELP_DOCTOR)
    doctor_parser.add_argument(
        CLI_ARG_DRY_RUN,
        metavar="URL",
        help=CLI_HELP_DRY_RUN,
    )

    # info
    subparsers.add_parser(CLI_COMMAND_INFO, help=CLI_HELP_INFO)

    args = parser.parse_args()

    if args.command == CLI_COMMAND_DOCTOR:
        return doctor_command(args)
    if args.command == CLI_COMMAND_INFO:
        return info_command(args)

    parser.print_help()
    return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())

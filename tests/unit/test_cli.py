"""Unit tests for CLI functionality."""

import argparse
import importlib.metadata
from unittest.mock import Mock, patch
import pytest
import requests

from mlflow_secrets_auth.cli import (
    info_command,
    doctor_command,
    main,
    get_enabled_provider,
)


class TestGetEnabledProvider:
    """Test get_enabled_provider function."""

    def test_no_provider_enabled(self):
        """Test when no provider is enabled."""
        with patch('mlflow_secrets_auth.cli.is_provider_enabled', return_value=False):
            name, provider = get_enabled_provider()
            assert name is None
            assert provider is None

    def test_vault_provider_enabled(self):
        """Test when vault provider is enabled and can be instantiated."""
        mock_provider = Mock()

        def is_enabled_side_effect(provider_name):
            return provider_name == "vault"

        with patch('mlflow_secrets_auth.cli.is_provider_enabled', side_effect=is_enabled_side_effect), \
             patch.dict('mlflow_secrets_auth.cli.PROVIDERS', {'vault': Mock(return_value=mock_provider)}):
            name, provider = get_enabled_provider()
            assert name == "vault"
            assert provider == mock_provider

    def test_provider_enabled_but_construction_fails(self):
        """Test when provider is enabled but construction fails."""
        def is_enabled_side_effect(provider_name):
            return provider_name == "vault"

        def failing_constructor():
            msg = "Failed to construct provider"
            raise Exception(msg)

        with patch('mlflow_secrets_auth.cli.is_provider_enabled', side_effect=is_enabled_side_effect), \
             patch.dict('mlflow_secrets_auth.cli.PROVIDERS', {'vault': failing_constructor}):
            name, provider = get_enabled_provider()
            assert name == "vault"
            assert provider is None

    def test_first_enabled_provider_returned(self):
        """Test that the first enabled provider is returned."""
        mock_vault = Mock()
        mock_aws = Mock()

        def is_enabled_side_effect(provider_name):
            return provider_name in ["vault", "aws-secrets-manager"]

        # Ensure ordered providers dict for predictable test
        ordered_providers = {
            "vault": Mock(return_value=mock_vault),
            "aws-secrets-manager": Mock(return_value=mock_aws),
            "azure-key-vault": Mock(),
        }

        with patch('mlflow_secrets_auth.cli.is_provider_enabled', side_effect=is_enabled_side_effect), \
             patch.dict('mlflow_secrets_auth.cli.PROVIDERS', ordered_providers, clear=True):
            name, provider = get_enabled_provider()
            assert name == "vault"  # First enabled provider
            assert provider == mock_vault


class TestInfoCommand:
    """Test info_command function."""

    def test_info_command_happy_path(self, capsys):
        """Test info command with version present and provider enabled."""
        args = argparse.Namespace()

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('importlib.metadata.version', return_value="1.2.3"), \
             patch('mlflow_secrets_auth.cli.is_provider_enabled', return_value=True), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts'):

            result = info_command(args)
            assert result == 0

    def test_info_command_version_not_found(self, capsys):
        """Test info command when package version cannot be found."""
        args = argparse.Namespace()

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('importlib.metadata.version', side_effect=importlib.metadata.PackageNotFoundError), \
             patch('mlflow_secrets_auth.cli.is_provider_enabled', return_value=False), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts'):

            result = info_command(args)
            assert result == 0

    def test_info_command_no_providers_enabled(self):
        """Test info command when no providers are enabled."""
        args = argparse.Namespace()

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('importlib.metadata.version', return_value="1.2.3"), \
             patch('mlflow_secrets_auth.cli.is_provider_enabled', return_value=False), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts'):

            result = info_command(args)
            assert result == 0


class TestDoctorCommand:
    """Test doctor_command function."""

    def test_doctor_no_provider_enabled(self):
        """Test doctor when no provider is enabled."""
        args = argparse.Namespace(dry_run=None)

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=(None, None)):

            result = doctor_command(args)
            assert result == 1

    def test_doctor_provider_construction_fails(self):
        """Test doctor when provider is enabled but construction fails."""
        args = argparse.Namespace(dry_run=None)

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", None)):

            result = doctor_command(args)
            assert result == 1

    def test_doctor_config_validation_fails(self):
        """Test doctor when provider config validation fails."""
        args = argparse.Namespace(dry_run=None)
        mock_provider = Mock()
        mock_provider._get_auth_mode.side_effect = Exception("Config error")

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)):

            result = doctor_command(args)
            assert result == 1

    def test_doctor_secret_fetch_fails(self):
        """Test doctor when secret fetch fails."""
        args = argparse.Namespace(dry_run=None)
        mock_provider = Mock()
        mock_provider._get_auth_mode.return_value = "token"
        mock_provider._get_ttl.return_value = 3600
        mock_provider._fetch_secret_cached.side_effect = Exception("Fetch error")

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)), \
             patch('mlflow_secrets_auth.cli.get_auth_header_name', return_value="Authorization"), \
             patch('mlflow_secrets_auth.cli.get_cache_size', return_value=100), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts', return_value=None):

            result = doctor_command(args)
            assert result == 1

    def test_doctor_secret_fetch_returns_none(self):
        """Test doctor when secret fetch returns None."""
        args = argparse.Namespace(dry_run=None)
        mock_provider = Mock()
        mock_provider._get_auth_mode.return_value = "token"
        mock_provider._get_ttl.return_value = 3600
        mock_provider._fetch_secret_cached.return_value = None

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)), \
             patch('mlflow_secrets_auth.cli.get_auth_header_name', return_value="Authorization"), \
             patch('mlflow_secrets_auth.cli.get_cache_size', return_value=100), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts', return_value=None):

            result = doctor_command(args)
            assert result == 1

    def test_doctor_auth_creation_fails(self):
        """Test doctor when auth creation fails."""
        args = argparse.Namespace(dry_run=None)
        mock_provider = Mock()
        mock_provider._get_auth_mode.return_value = "token"
        mock_provider._get_ttl.return_value = 3600
        mock_provider._fetch_secret_cached.return_value = {"username": "user", "password": "pass"}
        mock_provider._create_auth.side_effect = Exception("Auth creation failed")

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)), \
             patch('mlflow_secrets_auth.cli.get_auth_header_name', return_value="Authorization"), \
             patch('mlflow_secrets_auth.cli.get_cache_size', return_value=100), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts', return_value=None):

            result = doctor_command(args)
            assert result == 1

    def test_doctor_happy_path_without_dry_run(self):
        """Test doctor happy path without dry-run."""
        args = argparse.Namespace(dry_run=None)
        mock_provider = Mock()
        mock_provider._get_auth_mode.return_value = "token"
        mock_provider._get_ttl.return_value = 3600
        mock_provider._fetch_secret_cached.return_value = {"username": "user", "password": "pass"}
        mock_auth = Mock()
        mock_provider._create_auth.return_value = mock_auth

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)), \
             patch('mlflow_secrets_auth.cli.get_auth_header_name', return_value="Authorization"), \
             patch('mlflow_secrets_auth.cli.get_cache_size', return_value=100), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts', return_value=None):

            result = doctor_command(args)
            assert result == 0

    def test_doctor_dry_run_invalid_url(self):
        """Test doctor with dry-run and invalid URL."""
        args = argparse.Namespace(dry_run="invalid-url")
        mock_provider = Mock()
        mock_provider._get_auth_mode.return_value = "token"
        mock_provider._get_ttl.return_value = 3600
        mock_provider._fetch_secret_cached.return_value = {"username": "user", "password": "pass"}
        mock_auth = Mock()
        mock_provider._create_auth.return_value = mock_auth

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)), \
             patch('mlflow_secrets_auth.cli.get_auth_header_name', return_value="Authorization"), \
             patch('mlflow_secrets_auth.cli.get_cache_size', return_value=100), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts', return_value=None):

            result = doctor_command(args)
            assert result == 1

    def test_doctor_dry_run_host_not_allowed(self):
        """Test doctor with dry-run when host is not in allowlist."""
        args = argparse.Namespace(dry_run="https://forbidden.example.com/api/v1")
        mock_provider = Mock()
        mock_provider._get_auth_mode.return_value = "token"
        mock_provider._get_ttl.return_value = 3600
        mock_provider._fetch_secret_cached.return_value = {"username": "user", "password": "pass"}
        mock_auth = Mock()
        mock_provider._create_auth.return_value = mock_auth

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)), \
             patch('mlflow_secrets_auth.cli.get_auth_header_name', return_value="Authorization"), \
             patch('mlflow_secrets_auth.cli.get_cache_size', return_value=100), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts', return_value=["allowed.example.com"]):

            result = doctor_command(args)
            assert result == 1

    def test_doctor_dry_run_auth_none(self):
        """Test doctor with dry-run when get_request_auth returns None."""
        args = argparse.Namespace(dry_run="https://mlflow.example.com/api/v1")
        mock_provider = Mock()
        mock_provider._get_auth_mode.return_value = "token"
        mock_provider._get_ttl.return_value = 3600
        mock_provider._fetch_secret_cached.return_value = {"username": "user", "password": "pass"}
        mock_auth = Mock()
        mock_provider._create_auth.return_value = mock_auth
        mock_provider.get_request_auth.return_value = None

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)), \
             patch('mlflow_secrets_auth.cli.get_auth_header_name', return_value="Authorization"), \
             patch('mlflow_secrets_auth.cli.get_cache_size', return_value=100), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts', return_value=None):

            result = doctor_command(args)
            assert result == 1

    @pytest.mark.parametrize(('status_code', 'expected_exit'), [
        (200, 0),
        (401, 0),
        (403, 0),
        (500, 0),  # Even server errors should exit 0 for dry-run
    ])
    def test_doctor_dry_run_makes_head_request(self, status_code, expected_exit):
        """Test doctor with dry-run makes HEAD request and handles different status codes."""
        args = argparse.Namespace(dry_run="https://mlflow.example.com/api/v1")
        mock_provider = Mock()
        mock_provider._get_auth_mode.return_value = "token"
        mock_provider._get_ttl.return_value = 3600
        mock_provider._fetch_secret_cached.return_value = {"username": "user", "password": "pass"}
        mock_auth = Mock()
        mock_provider._create_auth.return_value = mock_auth
        mock_provider.get_request_auth.return_value = mock_auth

        mock_response = Mock()
        mock_response.status_code = status_code

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)), \
             patch('mlflow_secrets_auth.cli.get_auth_header_name', return_value="Authorization"), \
             patch('mlflow_secrets_auth.cli.get_cache_size', return_value=100), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts', return_value=None), \
             patch('requests.head', return_value=mock_response) as mock_head:

            result = doctor_command(args)
            assert result == expected_exit
            mock_head.assert_called_once_with(
                "https://mlflow.example.com/",
                auth=mock_auth,
                timeout=10,
                allow_redirects=True,
            )

    def test_doctor_dry_run_request_exception_suppressed(self):
        """Test doctor with dry-run when requests raises an exception (should be suppressed)."""
        args = argparse.Namespace(dry_run="https://mlflow.example.com/api/v1")
        mock_provider = Mock()
        mock_provider._get_auth_mode.return_value = "token"
        mock_provider._get_ttl.return_value = 3600
        mock_provider._fetch_secret_cached.return_value = {"username": "user", "password": "pass"}
        mock_auth = Mock()
        mock_provider._create_auth.return_value = mock_auth
        mock_provider.get_request_auth.return_value = mock_auth

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)), \
             patch('mlflow_secrets_auth.cli.get_auth_header_name', return_value="Authorization"), \
             patch('mlflow_secrets_auth.cli.get_cache_size', return_value=100), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts', return_value=None), \
             patch('requests.head', side_effect=requests.exceptions.ConnectionError("Connection failed")):

            result = doctor_command(args)
            assert result == 0  # Should still succeed since exception is suppressed

    def test_doctor_dry_run_other_exception(self):
        """Test doctor with dry-run when other exception occurs during dry-run."""
        args = argparse.Namespace(dry_run="https://mlflow.example.com/api/v1")
        mock_provider = Mock()
        mock_provider._get_auth_mode.return_value = "token"
        mock_provider._get_ttl.return_value = 3600
        mock_provider._fetch_secret_cached.return_value = {"username": "user", "password": "pass"}
        mock_auth = Mock()
        mock_provider._create_auth.return_value = mock_auth
        mock_provider.get_request_auth.side_effect = Exception("Unexpected error")

        with patch('mlflow_secrets_auth.cli.setup_logger'), \
             patch('mlflow_secrets_auth.cli._print_header'), \
             patch('mlflow_secrets_auth.cli.get_enabled_provider', return_value=("vault", mock_provider)), \
             patch('mlflow_secrets_auth.cli.get_auth_header_name', return_value="Authorization"), \
             patch('mlflow_secrets_auth.cli.get_cache_size', return_value=100), \
             patch('mlflow_secrets_auth.cli.get_allowed_hosts', return_value=None):

            result = doctor_command(args)
            assert result == 1


class TestMainFunction:
    """Test main function and argument parsing."""

    def test_main_doctor_command(self):
        """Test main function with doctor command."""
        test_args = ["doctor"]

        with patch('sys.argv', ['cli', *test_args]), \
             patch('mlflow_secrets_auth.cli.doctor_command', return_value=0) as mock_doctor:

            result = main()
            assert result == 0
            mock_doctor.assert_called_once()

    def test_main_doctor_command_with_dry_run(self):
        """Test main function with doctor command and dry-run flag."""
        test_args = ["doctor", "--dry-run", "https://mlflow.example.com"]

        with patch('sys.argv', ['cli', *test_args]), \
             patch('mlflow_secrets_auth.cli.doctor_command', return_value=0) as mock_doctor:

            result = main()
            assert result == 0
            mock_doctor.assert_called_once()
            args = mock_doctor.call_args[0][0]
            assert args.dry_run == "https://mlflow.example.com"

    def test_main_info_command(self):
        """Test main function with info command."""
        test_args = ["info"]

        with patch('sys.argv', ['cli', *test_args]), \
             patch('mlflow_secrets_auth.cli.info_command', return_value=0) as mock_info:

            result = main()
            assert result == 0
            mock_info.assert_called_once()

    def test_main_no_command_prints_help(self):
        """Test main function with no command prints help."""
        test_args = []

        with patch('sys.argv', ['cli', *test_args]), \
             patch('argparse.ArgumentParser.print_help') as mock_help:

            result = main()
            assert result == 1
            mock_help.assert_called_once()

    def test_main_unknown_command_prints_help(self):
        """Test main function with unknown command prints help."""
        test_args = ["unknown"]

        with patch('sys.argv', ['cli', *test_args]):
            # argparse raises SystemExit(2) for invalid commands
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2


class TestArgumentParsing:
    """Test argument parsing edge cases."""

    def test_doctor_parser_with_dry_run_argument(self):
        """Test that doctor parser correctly handles dry-run argument."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        doctor_parser = subparsers.add_parser("doctor")
        doctor_parser.add_argument("--dry-run", metavar="URL")

        args = parser.parse_args(["doctor", "--dry-run", "https://example.com"])
        assert args.command == "doctor"
        assert args.dry_run == "https://example.com"

    def test_info_parser_no_arguments(self):
        """Test that info parser doesn't require arguments."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("info")

        args = parser.parse_args(["info"])
        assert args.command == "info"


class TestPrintHeader:
    """Test _print_header function."""

    def test_print_header_function_exists(self):
        """Test that _print_header function can be imported and called."""
        from mlflow_secrets_auth.cli import _print_header

        # Should not raise an exception
        _print_header("Test Header")
